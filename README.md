# Secure PriceTable Checkout for Stripe Server
## Overview

The test AI Payment Server is a robust and secure backend solution for managing subscription-based payments for a Chrome extension. It integrates with Stripe for payment processing, uses FastAPI for efficient API handling, and PostgreSQL for persistent data storage. The server supports multiple subscription plans (monthly, yearly, and enterprise) and includes features like license key management, rate limiting, CORS, and security headers to ensure a secure and reliable experience.

This project is authored by **Thibaut LOMBARD** and licensed under the **Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0)** license.

## Features

- **Subscription Management**: Handles monthly, yearly, and enterprise plans via Stripe integration.
- **License Key System**: Generates and validates unique license keys tied to user fingerprints.
- **Secure API**: Implements HTTP Basic Authentication, rate limiting with SlowAPI, and CORS middleware.
- **Database Integration**: Uses SQLAlchemy with PostgreSQL for storing license and customer data.
- **HTTPS Support**: Configurable with Let's Encrypt or self-signed certificates.
- **Responsive Frontend**: A modern pricing page with light/dark mode and multilingual support (French/English).
- **Systemd Integration**: Optional setup as a systemd service for production deployment.
- **Logging**: Comprehensive logging to file and console for debugging and monitoring.

## Project Structure

```plaintext
├── install_python_server.py  # Script to install and configure the server
├── public                   # Static assets for the frontend
│   ├── cancel.html          # Payment cancellation page
│   ├── client.js            # Client-side JavaScript for Stripe integration
│   ├── fonts                # Roboto font files for styling
│   │   ├── Roboto-BlackItalic.ttf
│   │   ├── Roboto-Black.ttf
│   │   ├── Roboto-BoldItalic.ttf
│   │   ├── Roboto-Bold.ttf
│   │   ├── Roboto-Italic.ttf
│   │   ├── Roboto-LightItalic.ttf
│   │   ├── Roboto-Light.ttf
│   │   ├── Roboto-MediumItalic.ttf
│   │   ├── Roboto-Medium.ttf
│   │   ├── Roboto-Regular.ttf
│   │   ├── Roboto-ThinItalic.ttf
│   │   └── Roboto-Thin.ttf
│   ├── icons                # Logo and other icons
│   │   └── logo512.png
│   ├── index.html           # Main pricing page
│   └── styles.css           # CSS styles for the frontend
├── readme.md                # This README file
└── server.py                # Main FastAPI server application
```

## Prerequisites

- **Python 3.8+**
- **PostgreSQL** (for database storage)
- **Stripe Account** (for payment processing)
- **OpenSSL** (for generating self-signed certificates, if needed)
- **Systemd** (optional, for production deployment)
- **Let's Encrypt** (optional, for HTTPS certificates)

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Lombard-Web-Services/test-AI-Payment-Server.git
   cd test-AI-Payment-Server
   ```

2. **Run the Installation Script**:
   The `install_python_server.py` script automates the setup process. Run it with appropriate arguments:
   ```bash
   python3 install_python_server.py --domain your-domain.com --stripe-key your_stripe_api_key --webhook-secret your_webhook_secret
   ```
   Available arguments:
   - `--port`: Specify the server port (default: 4242).
   - `--no-https`: Run without HTTPS (not recommended for production).
   - `--no-service`: Run as a standalone application instead of a systemd service.
   - `--no-logging`: Disable logging to file.
   - `--localhost`: Use localhost for certificates and domain.
   - `--domain`: Specify the domain for HTTPS (default: your-domain.com).
   - `--stripe-key`: Stripe API key.
   - `--webhook-secret`: Stripe webhook secret.

3. **Follow Prompts**:
   - Provide PostgreSQL admin credentials and application database details.
   - Choose whether to generate self-signed certificates or use Let's Encrypt.
   - Enter API authentication credentials.

4. **Verify Installation**:
   If installed as a systemd service, check its status:
   ```bash
   sudo systemctl status test_ai_payment.service
   ```

## Configuration

Configuration is managed via environment variables in the `.env` file and a `config.json` file. Key settings include:

- **STRIPE_API_KEY**: Your Stripe secret key.
- **WEBHOOK_SECRET**: Your Stripe webhook secret.
- **YOUR_DOMAIN**: The domain where the server is hosted (e.g., `https://your-domain.com`).
- **DATABASE_URL**: PostgreSQL connection string (e.g., `postgresql://admin:password@localhost:5432/test_ai`).
- **ADMIN_USERNAME** and **ADMIN_PASSWORD_HASH**: Credentials for API authentication.

Example `.env` file:
```plaintext
STRIPE_API_KEY=sk_test_51RqJoCAZLeR1HJAQvY85EEf20wJhR2jadoj4k2KLlRwMc31XiN7NSaPomrPRO0mVUir8akc82UqgYuMJREEonuWG007DrI4EqN
WEBHOOK_SECRET=whsec_12345
YOUR_DOMAIN=https://your-domain.com
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$YOUR_BCRYPT_HASH
```

## Usage

1. **Start the Server**:
   If not using systemd, run the server manually:
   ```bash
   python3 server.py
   ```

2. **Access the Pricing Page**:
   Navigate to `http://your-domain.com:4242` (or `https` if configured) to view the pricing page. Choose a plan and proceed to payment via Stripe.

3. **Manage Subscriptions**:
   Use the `/create-portal-session` endpoint to access the Stripe Customer Portal for managing subscriptions.

4. **Check License**:
   The `/check-license` endpoint verifies license keys. It requires HTTP Basic Authentication and a JSON payload with `license_key` and `fingerprint`.

## API Endpoints

- **GET /**: Serves the pricing page (`index.html`).
- **POST /create-checkout-session**: Creates a Stripe checkout session for a subscription plan.
- **POST /create-portal-session**: Creates a Stripe Customer Portal session for managing subscriptions.
- **POST /webhook**: Handles Stripe webhook events (e.g., `checkout.session.completed`, `customer.subscription.deleted`).
- **POST /check-license**: Validates a license key and fingerprint (requires authentication).

## Frontend

The frontend (`index.html`, `styles.css`, `client.js`) provides a responsive pricing page with:
- Light/dark mode toggle.
- Language switcher (French/English).
- Stripe integration for payments.
- A cancellation page (`cancel.html`) with Tailwind CSS styling.

## Security

- **HTTPS**: Supports Let's Encrypt or self-signed certificates.
- **CORS**: Configured to allow specific origins.
- **Security Headers**: Includes `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, and `Strict-Transport-Security`.
- **Rate Limiting**: Limits API requests to prevent abuse.
- **Authentication**: Uses bcrypt for secure password hashing.

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0)** license. You may share this work, provided you give appropriate credit to the author (Thibaut LOMBARD), do not use it for commercial purposes, and do not distribute modified versions. See [LICENSE](https://creativecommons.org/licenses/by-nc-nd/4.0/) for details.

## Author

**Thibaut LOMBARD**  
- X: [x.com/lombardweb](https://x.com/lombardweb)  
- GitHub: [github.com/Lombard-Web-Services](https://github.com/Lombard-Web-Services)

## Contributing

This project is not open for contributions due to the CC BY-NC-ND license. For inquiries or custom solutions, contact [contact@lombardweb.com](mailto:contact@lombardweb.com).

---

