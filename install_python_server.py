#!/usr/bin/env python3
import os
import subprocess
import shutil
import sys
import logging
import glob
import json
import argparse
from passlib.context import CryptContext
import psycopg2

# Configure logging for setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Project configuration
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
CERT_DIR = os.path.join(PROJECT_DIR, "certs")
SERVICE_FILE = "/etc/systemd/system/test_ai_payment.service"
LETSENCRYPT_PATH = "/etc/letsencrypt/live"
CONFIG_FILE = os.path.join(PROJECT_DIR, "config.json")
CREDENTIALS_FILE = os.path.join(PROJECT_DIR, "credentials.json")
LOG_DIR = os.path.join(PROJECT_DIR, "logs")
ENV_FILE = os.path.join(PROJECT_DIR, ".env")
VENV_DIR = os.path.join(PROJECT_DIR, "venv")
SERVER_FILE = os.path.join(PROJECT_DIR, "server.py")

def create_virtualenv():
    """Create a virtual environment to avoid dependency conflicts."""
    logger.info(f"Creating virtual environment in {VENV_DIR}...")
    try:
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
        logger.info("Virtual environment created successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create virtual environment: {e}")
        return False

def get_pip_executable():
    """Get the pip executable from the virtual environment."""
    if os.path.exists(VENV_DIR):
        return os.path.join(VENV_DIR, "bin", "pip")
    return "pip3"

def get_python_executable():
    """Get the Python executable from the virtual environment."""
    if os.path.exists(VENV_DIR):
        return os.path.join(VENV_DIR, "bin", "python")
    return sys.executable

def install_dependencies():
    """Install required Python dependencies in the virtual environment."""
    dependencies = [
        "fastapi",
        "uvicorn",
        "stripe",
        "sqlalchemy",
        "psycopg2-binary",
        "slowapi",
        "passlib[bcrypt]",
        "pyOpenSSL>=24.0.0",
        "python-dotenv"  # Added for .env file loading
    ]
    pip_exe = get_pip_executable()
    logger.info(f"Installing dependencies using {pip_exe}...")
    try:
        subprocess.run([pip_exe, "install", "--upgrade", "pip"], check=True)
        subprocess.run([pip_exe, "install"] + dependencies, check=True)
        logger.info("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        logger.error("Try installing 'cryptography' manually or use a compatible version.")
        return False

def find_certificate_file(base_path, prefix):
    """Find the first available certificate file (e.g., privkey.pem, privkey1.pem, etc.)."""
    for i in range(1, 10):
        file_name = f"{prefix}{i}.pem" if i > 1 else f"{prefix}.pem"
        file_path = os.path.join(base_path, file_name)
        if os.path.exists(file_path):
            return file_path
    return None

def copy_letsencrypt_certs(domain):
    """Copy Let's Encrypt certificates, resolving symlinks and handling numbered variants."""
    domain_path = os.path.join(LETSENCRYPT_PATH, domain)
    real_path = os.path.realpath(domain_path)
    logger.info(f"Resolved domain path: {real_path}")

    fullchain_src = find_certificate_file(real_path, "fullchain")
    privkey_src = find_certificate_file(real_path, "privkey")

    if not fullchain_src or not privkey_src:
        logger.error(f"Required certificate files not found in {real_path}")
        return False

    os.makedirs(CERT_DIR, exist_ok=True)
    fullchain_dest = os.path.join(CERT_DIR, "cert.pem")
    privkey_dest = os.path.join(CERT_DIR, "key.pem")

    try:
        shutil.copy(fullchain_src, fullchain_dest)
        shutil.copy(privkey_src, privkey_dest)
        logger.info(f"Copied certificates: {fullchain_src} -> {fullchain_dest}, {privkey_src} -> {privkey_dest}")
        return True
    except (shutil.Error, PermissionError) as e:
        logger.error(f"Failed to copy certificates: {e}")
        return False

def generate_self_signed_cert(localhost=False):
    """Generate self-signed certificates with openssl."""
    logger.info("Generating self-signed certificates...")
    os.makedirs(CERT_DIR, exist_ok=True)
    cert_file = os.path.join(CERT_DIR, "cert.pem")
    key_file = os.path.join(CERT_DIR, "key.pem")
    subject = "/CN=localhost" if localhost else "/CN=your-domain.com"
    try:
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:4096", "-nodes",
            "-out", cert_file, "-keyout", key_file, "-days", "365",
            "-subj", subject
        ], check=True)
        logger.info(f"Certificates generated: {cert_file}, {key_file}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate certificates: {e}")
        return False

def setup_postgresql():
    """Set up PostgreSQL database and create the licenses table."""
    logger.info("Setting up PostgreSQL database...")
    try:
        # Check if PostgreSQL is installed
        subprocess.run(["psql", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Ensure PostgreSQL service is running
        logger.info("Checking PostgreSQL service status...")
        status = subprocess.run(["systemctl", "is-active", "postgresql"], capture_output=True, text=True)
        if status.stdout.strip() != "active":
            logger.info("Starting PostgreSQL service...")
            subprocess.run(["sudo", "systemctl", "start", "postgresql"], check=True)
            logger.info("Enabling PostgreSQL service on boot...")
            subprocess.run(["sudo", "systemctl", "enable", "postgresql"], check=True)
        
        # Prompt for PostgreSQL admin user (postgres) credentials
        postgres_user = input("Enter PostgreSQL admin user (default: postgres): ").strip() or "postgres"
        postgres_password = input("Enter PostgreSQL admin password: ").strip()
        
        # Test PostgreSQL admin connection
        try:
            conn = psycopg2.connect(
                dbname="postgres", user=postgres_user, password=postgres_password, host="localhost", port="5432"
            )
            conn.close()
            logger.info("PostgreSQL admin connection verified")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to PostgreSQL as {postgres_user}: {e}")
            logger.error("Ensure the PostgreSQL service is running and the password is correct.")
            logger.error("To reset the postgres password, run: sudo -u postgres psql -c \"ALTER USER postgres WITH PASSWORD 'new_password';\"")
            return False

        # Prompt for application database credentials
        db_user = input("Enter application PostgreSQL username (default: admin): ").strip() or "admin"
        db_password = input("Enter application PostgreSQL password: ").strip() or "password"
        db_name = input("Enter database name (default: test_ai): ").strip() or "test_ai"
        db_host = input("Enter database host (default: localhost): ").strip() or "localhost"
        db_port = input("Enter database port (default: 5432): ").strip() or "5432"

        # Create application user and database
        try:
            conn = psycopg2.connect(
                dbname="postgres", user=postgres_user, password=postgres_password, host=db_host, port=db_port
            )
            conn.autocommit = True
            cursor = conn.cursor()
            # Create user if it doesn't exist
            cursor.execute(f"SELECT 1 FROM pg_roles WHERE rolname = '{db_user}'")
            if not cursor.fetchone():
                cursor.execute(f"CREATE USER {db_user} WITH PASSWORD '{db_password}'")
                logger.info(f"User {db_user} created")
            else:
                logger.info(f"User {db_user} already exists")
            # Create database if it doesn't exist
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
            if not cursor.fetchone():
                cursor.execute(f"CREATE DATABASE {db_name} OWNER {db_user}")
                logger.info(f"Database {db_name} created")
            else:
                logger.info(f"Database {db_name} already exists")
            # Grant privileges
            cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}")
            cursor.close()
            conn.close()
        except psycopg2.Error as e:
            logger.error(f"Failed to create user or database: {e}")
            return False

        # Save database URL to .env
        env_content = f"DATABASE_URL=postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}\n"
        with open(ENV_FILE, "a") as f:
            f.write(env_content)
        logger.info("Database URL saved to .env")

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"PostgreSQL setup failed: {e}")
        return False

def get_port(default=4242):
    """Prompt user for port number within valid range."""
    while True:
        try:
            port = input(f"Enter the port for the payment server (1024-65535, default: {default}): ").strip()
            if not port:
                return default
            port = int(port)
            if 1024 <= port <= 65535:
                return port
            else:
                print("Port must be between 1024 and 65535.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

def get_credentials():
    """Prompt user for username and password, hash the password."""
    username = input("Enter username for API authentication (default: admin): ").strip() or "admin"
    while True:
        password = input("Enter password for API authentication: ").strip()
        if password:
            break
        print("Password cannot be empty.")
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(password)
    return {"username": username, "hashed_password": hashed_password}

def save_credentials(credentials):
    """Save credentials to a secure file."""
    try:
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(credentials, f)
        os.chmod(CREDENTIALS_FILE, 0o600)
        logger.info(f"Credentials saved to {CREDENTIALS_FILE}")
    except (IOError, PermissionError) as e:
        logger.error(f"Failed to save credentials: {e}")
        sys.exit(1)

def create_systemd_service(port, use_https):
    """Create and enable systemd service for the payment server."""
    cert_file = os.path.join(CERT_DIR, "cert.pem")
    key_file = os.path.join(CERT_DIR, "key.pem")
    python_exe = get_python_executable()
    uvicorn_cmd = f"{python_exe} -m uvicorn server:app --host 0.0.0.0 --port {port}"
    if use_https:
        uvicorn_cmd += f" --ssl-certfile {cert_file} --ssl-keyfile {key_file}"

    service_content = f"""
[Unit]
Description=test AI Payment Server
After=network.target

[Service]
ExecStart={uvicorn_cmd}
WorkingDirectory={PROJECT_DIR}
Restart=always
User={os.getlogin()}
Environment=PYTHONUNBUFFERED=1
EnvironmentFile={ENV_FILE}

[Install]
WantedBy=multi-user.target
"""
    try:
        with open("test_ai_payment.service", "w") as f:
            f.write(service_content)
        subprocess.run(["sudo", "mv", "test_ai_payment.service", SERVICE_FILE], check=True)
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "enable", "test_ai_payment.service"], check=True)
        logger.info("Systemd service created and enabled")
    except (subprocess.CalledProcessError, PermissionError) as e:
        logger.error(f"Failed to create systemd service: {e}")
        sys.exit(1)

def save_config(use_https, port, enable_logging, domain, stripe_api_key, webhook_secret):
    """Save configuration to config.json."""
    config = {
        "use_https": use_https,
        "port": port,
        "enable_logging": enable_logging,
        "domain": domain,
        "stripe_api_key": stripe_api_key,
        "webhook_secret": webhook_secret
    }
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        logger.info(f"Configuration saved: {config}")
    except (IOError, PermissionError) as e:
        logger.error(f"Failed to save configuration: {e}")
        sys.exit(1)

def save_env(stripe_api_key, webhook_secret, domain, admin_username, admin_password_hash):
    """Save environment variables to .env file."""
    env_content = f"""
STRIPE_API_KEY={stripe_api_key}
WEBHOOK_SECRET={webhook_secret}
YOUR_DOMAIN={'https' if not args.no_https else 'http'}://{domain}
ADMIN_USERNAME={admin_username}
ADMIN_PASSWORD_HASH={admin_password_hash}
"""
    try:
        with open(ENV_FILE, "w") as f:
            f.write(env_content)
        os.chmod(ENV_FILE, 0o600)
        logger.info("Environment variables saved to .env")
    except (IOError, PermissionError) as e:
        logger.error(f"Failed to save .env file: {e}")
        sys.exit(1)

def install():
    """Main installation function with command-line arguments."""
    parser = argparse.ArgumentParser(description="Install test AI Payment Server")
    parser.add_argument("--port", type=int, default=4242, help="Port for the server (default: 4242)")
    parser.add_argument("--no-https", action="store_true", help="Disable HTTPS")
    parser.add_argument("--no-service", action="store_true", help="Run as standalone instead of systemd service")
    parser.add_argument("--no-logging", action="store_true", help="Disable logging to file")
    parser.add_argument("--localhost", action="store_true", help="Use localhost for certificates and domain")
    parser.add_argument("--domain", default="your-domain.com", help="Domain for HTTPS (default: your-domain.com)")
    parser.add_argument("--stripe-key", default="sk_test_51RqJoCAZLeR1HJAQvY85EEf20wJhR2jadoj4k2KLlRwMc31XiN7NSaPomrPRO0mVUir8akc82UqgYuMJREEonuWG007DrI4EqN", help="Stripe API key")
    parser.add_argument("--webhook-secret", default="whsec_12345", help="Stripe webhook secret")
    global args
    args = parser.parse_args()

    logger.info("Starting test AI Payment Server installation...")

    # Create virtual environment
    if not create_virtualenv():
        logger.error("Virtual environment creation failed; exiting")
        sys.exit(1)

    # Ensure directories exist
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(CERT_DIR, exist_ok=True)
    os.makedirs(os.path.join(PROJECT_DIR, "public"), exist_ok=True)

    # Install dependencies
    if not install_dependencies():
        logger.error("Dependency installation failed; exiting")
        sys.exit(1)

    # Setup PostgreSQL
    if not setup_postgresql():
        logger.error("PostgreSQL setup failed; exiting")
        sys.exit(1)

    # Prompt for credentials
    credentials = get_credentials()
    admin_username = credentials["username"]
    admin_password_hash = credentials["hashed_password"]
    save_credentials(credentials)

    # HTTPS configuration
    use_https = not args.no_https
    cert_file = os.path.join(CERT_DIR, "cert.pem")
    key_file = os.path.join(CERT_DIR, "key.pem")
    certs_copied = False
    domain = args.domain if not args.localhost else "localhost"

    if use_https:
        if os.path.exists(LETSENCRYPT_PATH) and not args.localhost:
            domains = [d for d in os.listdir(LETSENCRYPT_PATH) if os.path.isdir(os.path.join(LETSENCRYPT_PATH, d))]
            if domains:
                logger.info(f"Found Let's Encrypt certificates in {LETSENCRYPT_PATH}")
                print(f"Available domains: {domains}")
                selected_domain = input("Select a domain to copy certificates from (or press Enter to skip): ").strip()
                if selected_domain in domains:
                    certs_copied = copy_letsencrypt_certs(selected_domain)
                    domain = selected_domain
                else:
                    logger.warning("No domain selected or invalid domain; proceeding to certificate generation")
            else:
                logger.warning("No Let's Encrypt certificates found")
        else:
            logger.warning("Let's Encrypt path not found or localhost mode enabled")

        if not certs_copied and not (os.path.exists(cert_file) and os.path.exists(key_file)):
            logger.info("No valid certificates found")
            generate_cert = input("Generate self-signed certificates with openssl? (y/n): ").lower() == "y"
            if generate_cert:
                if not generate_self_signed_cert(localhost=args.localhost):
                    logger.error("Failed to generate certificates; exiting")
                    sys.exit(1)
            else:
                logger.error("No certificates provided; HTTPS requires certificates. Use --no-https to run without HTTPS.")
                sys.exit(1)

    # Prompt for logging
    enable_logging = not args.no_logging
    if enable_logging:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(os.path.join(LOG_DIR, "test_ai_payment.log")),
                logging.StreamHandler()
            ]
        )
        logger.info("Logging to file enabled")

    # Save configuration
    save_config(use_https, args.port, enable_logging, domain, args.stripe_key, args.webhook_secret)
    save_env(args.stripe_key, args.webhook_secret, domain, admin_username, admin_password_hash)

    # Install as systemd service
    install_as_service = not args.no_service
    if install_as_service:
        create_systemd_service(args.port, use_https)
        try:
            subprocess.run(["sudo", "systemctl", "start", "test_ai_payment.service"], check=True)
            logger.info("Payment server service started")
            print("Service installed and started. Check status with: sudo systemctl status test_ai_payment.service")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start service: {e}")
            sys.exit(1)
    else:
        logger.info("Running as standalone application")
        python_exe = get_python_executable()
        cmd = [python_exe, "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", str(args.port)]
        if use_https:
            cmd.extend(["--ssl-certfile", cert_file, "--ssl-keyfile", key_file])
        subprocess.run(cmd)

if __name__ == "__main__":
    install()
