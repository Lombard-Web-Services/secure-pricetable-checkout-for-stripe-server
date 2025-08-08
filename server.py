#!/usr/bin/env python3
import os
import uuid
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import stripe
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, constr
from passlib.context import CryptContext
from fastapi.responses import RedirectResponse, JSONResponse, Response
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

# Ensure logs directory exists
os.makedirs(os.path.join(os.path.dirname(__file__), "logs"), exist_ok=True)

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at {env_path}")
load_dotenv(dotenv_path=env_path)

# Configuration
stripe.api_key = os.getenv("STRIPE_API_KEY", "sk_test_51RqJoCAZLeR1HJAQvY85EEf20wJhR2jadoj4k2KLlRwMc31XiN7NSaPomrPRO0mVUir8akc82UqgYuMJREEonuWG007DrI4EqN")
YOUR_DOMAIN = os.getenv("YOUR_DOMAIN", "http://localhost:4242")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@localhost:5432/test_ai")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "whsec_12345")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "$2b$12$YOUR_BCRYPT_HASH")

# Log DATABASE_URL for debugging
logger = logging.getLogger(__name__)
logger.info(f"Using DATABASE_URL: {DATABASE_URL}")

# FastAPI and Security Setup
app = FastAPI()
app.mount("/public", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "public")), name="public")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "logs", "test_ai_payment.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[YOUR_DOMAIN, "http://localhost:4242", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://js.stripe.com; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self' /public/fonts; "
            "img-src 'self' /public/icons; "
            "frame-src https://js.stripe.com;"
        )
        if YOUR_DOMAIN.startswith("https"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Database Setup
Base = declarative_base()

class License(Base):
    __tablename__ = "licenses"
    id = Column(Integer, primary_key=True, index=True)
    license_key = Column(String, unique=True, index=True)
    customer_id = Column(String, index=True)
    plan = Column(String)
    devices_allowed = Column(Integer)
    referer = Column(String)
    user_agent = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    fingerprint = Column(String, index=True)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# Pydantic Models
class LicenseCreate(BaseModel):
    customer_id: constr(min_length=1)
    plan: constr(pattern="^(monthly|yearly|enterprise)$")
    devices_allowed: int
    referer: constr(min_length=1)
    user_agent: constr(min_length=1)
    fingerprint: constr(min_length=1)

class LicenseCheck(BaseModel):
    license_key: constr(min_length=1)
    fingerprint: constr(min_length=1)

# Dependency for Database Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency for Basic Auth
async def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != ADMIN_USERNAME or not pwd_context.verify(credentials.password, ADMIN_PASSWORD_HASH):
        logger.warning("Unauthorized access attempt")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return credentials.username

# License Key Generation
def generate_license_key():
    return str(uuid.uuid4())

@app.get("/")
async def get_index():
    try:
        file_path = os.path.join(os.path.dirname(__file__), "public", "index.html")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return Response(content=f.read(), media_type="text/html")
        else:
            root_file_path = os.path.join(os.path.dirname(__file__), "index.html")
            if os.path.exists(root_file_path):
                with open(root_file_path, "r") as f:
                    return Response(content=f.read(), media_type="text/html")
            else:
                return Response(
                    content="<h1>test AI Payment Server</h1><p>Welcome to the payment server.</p>",
                    media_type="text/html"
                )
    except Exception as e:
        logger.error(f"Error serving index.html: {str(e)}")
        raise HTTPException(status_code=500, detail="Error serving index page")

@app.post("/create-checkout-session")
@limiter.limit("5/minute")
async def create_checkout_session(request: Request, lookup_key: str = None, db: Session = Depends(get_db)):
    try:
        prices = stripe.Price.list(lookup_keys=[lookup_key], expand=["data.product"])
        if not prices.data:
            logger.error(f"No price found for lookup_key: {lookup_key}")
            raise HTTPException(status_code=400, detail="Invalid price")

        checkout_session = stripe.checkout.Session.create(
            line_items=[{"price": prices.data[0].id, "quantity": 1}],
            mode="subscription",
            success_url=YOUR_DOMAIN + "/success.html?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=YOUR_DOMAIN + "/cancel.html",
            customer_email=request.headers.get("email", None),
            metadata={"plan": lookup_key}
        )
        return RedirectResponse(checkout_session.url, status_code=303)
    except Exception as e:
        logger.error(f"Checkout session creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create-portal-session")
@limiter.limit("5/minute")
async def customer_portal(request: Request, session_id: str = None, db: Session = Depends(get_db)):
    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        portal_session = stripe.billing_portal.Session.create(
            customer=checkout_session.customer,
            return_url=YOUR_DOMAIN
        )
        return RedirectResponse(portal_session.url, status_code=303)
    except Exception as e:
        logger.error(f"Portal session creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook")
async def webhook_received(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
        data = event["data"]
        event_type = event["type"]
        data_object = data["object"]

        logger.info(f"Webhook event received: {event_type}")

        if event_type == "checkout.session.completed":
            customer_id = data_object["customer"]
            plan = data_object["metadata"].get("plan", "unknown")
            devices_allowed = 1 if plan == "monthly" else 3 if plan == "yearly" else 10
            license_key = generate_license_key()
            license = License(
                license_key=license_key,
                customer_id=customer_id,
                plan=plan,
                devices_allowed=devices_allowed,
                referer=request.headers.get("referer", "unknown"),
                user_agent=request.headers.get("user-agent", "unknown"),
                fingerprint=data_object.get("client_reference_id", "unknown")
            )
            db.add(license)
            db.commit()
            logger.info(f"License created: {license_key} for customer {customer_id}")
        elif event_type == "customer.subscription.deleted":
            customer_id = data_object["customer"]
            license = db.query(License).filter(License.customer_id == customer_id).first()
            if license:
                db.delete(license)
                db.commit()
                logger.info(f"License deleted for customer {customer_id}")

        return JSONResponse({"status": "success"})
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/check-license")
@limiter.limit("10/minute")
async def check_license(request: Request, license_data: LicenseCheck, db: Session = Depends(get_db), username: str = Depends(get_current_user)):
    license = db.query(License).filter(License.license_key == license_data.license_key, License.fingerprint == license_data.fingerprint).first()
    if not license:
        logger.warning(f"Invalid license key or fingerprint: {license_data.license_key}")
        raise HTTPException(status_code=404, detail="License not found or invalid fingerprint")
    return {
        "license_key": license.license_key,
        "plan": license.plan,
        "devices_allowed": license.devices_allowed,
        "created_at": license.created_at
    }

if __name__ == "__main__":
    # Load configuration from config.json
    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = json.load(f)
        port = config.get("port", 4242)
        use_https = config.get("use_https", False)
    else:
        port = 4242
        use_https = False

    # Run Uvicorn server
    if use_https:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            ssl_keyfile=os.path.join(os.path.dirname(__file__), "certs", "key.pem"),
            ssl_certfile=os.path.join(os.path.dirname(__file__), "certs", "cert.pem")
        )
    else:
        uvicorn.run(app, host="0.0.0.0", port=port)
