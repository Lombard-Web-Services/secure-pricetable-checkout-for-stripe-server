# Secure PriceTable Checkout for Stripe Server

🌟 **Welcome to Secure PriceTable Checkout for Stripe Server** 🌟  
A robust, secure, and responsive FastAPI-based server for handling Stripe subscription payments with an elegant pricing table interface.  
This project provides a seamless checkout experience with multilingual support, dark/light mode, and a customizable design, built with modern web technologies.

Developed by **Thibaut Lombard**

---

## 🚀 Features

- **Secure Payment Processing**: Integrates with Stripe's Checkout API for safe, PCI-compliant subscription payments.
- **Responsive Pricing Table**: Elegant, mobile-friendly pricing cards with gradient buttons and a centered title.
- **Multilingual Support**: Toggle between English and French with a dropdown menu.
- **Dark/Light Mode**: Seamless theme switching with a toggle button, matching user preferences.
- **Customizable Design**: Uses Roboto fonts and a consistent gradient style (`linear-gradient(45deg, #2563eb, #7c3aed)`).
- **Secure API**: Protected with HTTP Basic Authentication and a strict Content-Security-Policy (CSP).
- **Webhook Support**: Handles Stripe webhook events for subscription management (e.g., creation, deletion).
- **Database Integration**: Stores license keys and customer data in PostgreSQL with SQLAlchemy.
- **Rate Limiting**: Prevents abuse with SlowAPI rate limiting (5 requests/minute for checkout, 10/minute for license checks).
- **Logging**: Comprehensive logging to `logs/moult_ai_payment.log` for debugging and monitoring.
- **Static File Serving**: Serves assets (CSS, JS, fonts, icons) from the `public` directory.

*Add On: Consider regularly updating features to reflect new Stripe API capabilities and user feedback.*

---

## 🛠️ Installation

Follow these steps to set up the project locally.  
**Ensure you have a Stripe account and PostgreSQL installed.**

### Prerequisites

- **Python**: 3.8 or higher  
- **PostgreSQL**: 12 or higher  
- **Stripe Account**: Obtain API keys from [Stripe Dashboard](https://dashboard.stripe.com)  
- **Git**: For cloning the repository  
- **Node.js**: Optional, for local development with Stripe CLI  

---

### Steps

1. **Clone the Repository**
    ```
    git clone https://github.com/Lombard-Web-Services/secure-pricetable-checkout-for-stripe-server.git
    cd secure-pricetable-checkout-for-stripe-server
    ```

2. **Set Up Virtual Environment**
    ```
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install Dependencies**
    ```
    pip install -r requirements.txt
    ```
    Ensure your `requirements.txt` includes all needed packages as listed.

4. **Configure Environment Variables**
    - Copy `.env.example` to `.env` and update with your credentials.

5. **Set Up PostgreSQL Database**
    - Create database `moult_ai`.

6. **Copy Static Assets**
    - Verify assets in `public/` folder.

7. **Run the Server**
    - Start with `python3 server.py`.

8. **(Optional) Test with Stripe CLI**
    - Authenticate and forward webhooks.

*Add On: For production deployment, consider using Docker or container orchestration for easier setup and scaling.*

---

## 🔒 Security

- **Content-Security-Policy (CSP)**: Restricts resource loading to trusted sources.
- **Basic Authentication**: Secures critical endpoints.
- **HTTPS Support**: Optional and configurable.
- **Rate Limiting**: Protects against brute-force and abuse.
- **PCI Compliance**: Ensured by using Stripe Checkout.

*Add On: Review and update security policies periodically to keep up with best practices and vulnerability patches.*

---

## 🧪 Testing

### Access the Pricing Page

Open [http://localhost:4242](http://localhost:4242) and verify UI features and absence of CSP errors.

### Test Checkout

- Use Stripe test cards to simulate payments and 3D Secure workflows.

*Add On: Implement automated tests and CI/CD pipelines to catch regressions early and improve reliability.*

---

**End of README**
