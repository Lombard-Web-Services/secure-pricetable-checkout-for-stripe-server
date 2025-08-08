// Initialize Stripe
const stripe = Stripe('pk_test_51RqJoCAZLeR1HJAQ2vX9f6zE0xK7m9tP8uQwL5nJ2kT4pH3rY8mN6vB2xA9jQ0wE7uT3nM5vK8xL9zQ2mW3rY6tN00zX9f6zE0');

// Generate a simple fingerprint
function generateFingerprint() {
    return btoa(navigator.userAgent + window.screen.width + window.screen.height);
}

// Handle Checkout button clicks
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const lookupKey = form.querySelector('input[name="lookup_key"]').value;
        try {
            const response = await fetch('/create-checkout-session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `lookup_key=${encodeURIComponent(lookupKey)}&client_reference_id=${encodeURIComponent(generateFingerprint())}`
            });
            if (response.redirected) {
                window.location.href = response.url;
            } else {
                console.error('Failed to create checkout session');
            }
        } catch (error) {
            console.error('Error:', error);
        }
    });
});

// Handle Portal session
document.querySelector('a[href="/create-portal-session"]').addEventListener('click', async (e) => {
    e.preventDefault();
    const searchParams = new URLSearchParams(window.location.search);
    const sessionId = searchParams.get('session_id');
    if (sessionId) {
        try {
            const response = await fetch('/create-portal-session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `session_id=${encodeURIComponent(sessionId)}`
            });
            if (response.redirected) {
                window.location.href = response.url;
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }
});

// Check License Key
async function checkLicense(licenseKey) {
    const fingerprint = generateFingerprint();
    try {
        const response = await fetch('/check-license', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic YWRtaW46cGFzc3dvcmQ='
            },
            body: JSON.stringify({ license_key: licenseKey, fingerprint })
        });
        if (response.ok) {
            const data = await response.json();
            console.log('License valid:', data);
            return data;
        } else {
            console.error('Invalid license');
            return null;
        }
    } catch (error) {
        console.error('Error checking license:', error);
        return null;
    }
}

// Example: Check license on page load
document.addEventListener('DOMContentLoaded', async () => {
    const licenseKey = localStorage.getItem('license_key') || 'example-key';
    if (licenseKey) {
        const licenseData = await checkLicense(licenseKey);
        if (licenseData) {
            console.log('Access granted for plan:', licenseData.plan);
        }
    }
});
