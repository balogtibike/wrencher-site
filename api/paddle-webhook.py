"""
api/paddle-webhook.py

Vercel serverless function.
Receives Paddle transaction.completed webhook,
generates an HMAC license key, and emails it via Resend.
"""

import hashlib
import hmac
import json
import os
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

# ── Configuration — set these in Vercel environment variables ──────────
PADDLE_WEBHOOK_SECRET = os.environ.get("PADDLE_WEBHOOK_SECRET", "")
RESEND_API_KEY        = os.environ.get("RESEND_API_KEY", "")
HMAC_SECRET           = os.environ.get("HMAC_SECRET", "")

# Valid Paddle price IDs
PRICE_ANNUAL   = "pri_01m1y6bn71bcmj966t5253bbwc"
PRICE_LIFETIME = "pri_01m1y6cmqrf925z7hcake2dps5"

FROM_EMAIL = "Wrencher <hello@wrencher.app>"
SUPPORT    = "hello@wrencher.app"


# ── HMAC key generation ────────────────────────────────────────────────

def generate_license_key(license_type: str, transaction_id: str) -> str:
    """
    Generate a deterministic HMAC license key.
    Format: WA-XXXXX-XXXXX-XXXXX-XXXXX (Annual)
            WL-XXXXX-XXXXX-XXXXX-XXXXX (Lifetime)
    The prefix encodes the license type for offline validation.
    HMAC input: transaction_id only (unique per purchase).
    """
    prefix = "WA" if license_type == "annual" else "WL"
    raw = hmac.new(
        HMAC_SECRET.encode("utf-8"),
        transaction_id.lower().encode("utf-8"),
        hashlib.sha256
    ).hexdigest().upper()
    chars = raw[:20]
    body = "-".join(chars[i:i+5] for i in range(0, 20, 5))
    return f"{prefix}-{body}"


# ── Paddle signature verification ─────────────────────────────────────

def verify_paddle_signature(body: bytes, signature_header: str) -> bool:
    """
    Verify the Paddle webhook signature.
    Paddle sends: Paddle-Signature: ts=<timestamp>;h1=<hmac>
    """
    if not signature_header or not PADDLE_WEBHOOK_SECRET:
        return False
    try:
        parts = dict(p.split("=", 1) for p in signature_header.split(";"))
        ts    = parts.get("ts", "")
        h1    = parts.get("h1", "")

        # Reject timestamps older than 5 minutes
        if abs(time.time() - int(ts)) > 300:
            return False

        signed_payload = f"{ts}:{body.decode('utf-8')}"
        expected = hmac.new(
            PADDLE_WEBHOOK_SECRET.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, h1)
    except Exception:
        return False


# ── Resend email delivery ──────────────────────────────────────────────

def send_license_email(to_email: str, license_key: str, license_type: str) -> bool:
    """Send license key email via Resend API."""
    type_label   = "Annual" if license_type == "annual" else "Lifetime"
    renewal_note = (
        "Your Annual license is valid for 12 months. "
        "When it expires, simply purchase again to continue — "
        "your card will never be charged automatically."
        if license_type == "annual"
        else "Your Lifetime license never expires. All future updates are included."
    )

    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:system-ui,sans-serif;max-width:540px;margin:0 auto;padding:32px 24px;color:#0f172a;">
  <img src="https://wrencher.app/assets/img/logo.png" alt="Wrencher" style="height:40px;margin-bottom:24px;">
  <h1 style="font-size:22px;margin-bottom:8px;">Your Wrencher license key</h1>
  <p style="color:#64748b;margin-bottom:24px;">
    Thank you for purchasing Wrencher {type_label}. Here is your license key:
  </p>
  <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:20px 24px;text-align:center;margin-bottom:24px;">
    <div style="font-family:monospace;font-size:22px;font-weight:700;letter-spacing:2px;color:#0f172a;">
      {license_key}
    </div>
  </div>
  <h2 style="font-size:15px;margin-bottom:12px;">How to activate:</h2>
  <ol style="color:#334155;padding-left:20px;line-height:1.8;">
    <li>Open Wrencher on your computer</li>
    <li>Go to <strong>Settings → License</strong></li>
    <li>Paste the key above into the activation field</li>
    <li>Click <strong>Activate</strong></li>
  </ol>
  <p style="color:#64748b;font-size:14px;margin-top:20px;">{renewal_note}</p>
  <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0;">
  <p style="color:#94a3b8;font-size:13px;">
    This key can be used on up to 2 computers. To transfer to a new machine,
    email <a href="mailto:{SUPPORT}" style="color:#334155;">{SUPPORT}</a>.<br><br>
    <strong>Key not working?</strong> Make sure you copy the full key including all dashes.
    If problems persist, email {SUPPORT} with your order number.<br><br>
    <strong>Didn&apos;t expect this email?</strong> You can safely ignore it —
    your card has not been charged without your action.
  </p>
  <p style="color:#94a3b8;font-size:12px;margin-top:16px;">
    Wrencher &nbsp;·&nbsp; <a href="https://wrencher.app" style="color:#94a3b8;">wrencher.app</a>
    &nbsp;·&nbsp; 30-day refund guarantee
  </p>
</body>
</html>
"""

    text_body = (
        f"Your Wrencher {type_label} license key:\n\n"
        f"  {license_key}\n\n"
        f"To activate:\n"
        f"1. Open Wrencher\n"
        f"2. Go to Settings → License\n"
        f"3. Paste the key and click Activate\n\n"
        f"{renewal_note}\n\n"
        f"This key works on up to 2 computers.\n"
        f"Questions? Email {SUPPORT}"
    )

    payload = json.dumps({
        "from":    FROM_EMAIL,
        "to":      [to_email],
        "subject": f"Your Wrencher {type_label} license key",
        "html":    html_body,
        "text":    text_body,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        method="POST"
    )
    req.add_header("Authorization", f"Bearer {RESEND_API_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "wrencher-webhook/1.0")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            print(f"Resend OK: {result.get('id')}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print(f"Resend error {e.code}: {body}")
        return False
    except Exception as e:
        print(f"Resend exception: {e}")
        return False


# ── Main handler ───────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # Verify Paddle signature
        sig = self.headers.get("Paddle-Signature", "")
        if not verify_paddle_signature(body, sig):
            print("Signature verification failed")
            self._respond(401, {"error": "Invalid signature"})
            return

        try:
            event = json.loads(body)
        except Exception:
            self._respond(400, {"error": "Invalid JSON"})
            return

        event_type = event.get("event_type", "")
        print(f"Paddle event: {event_type}")

        if event_type != "transaction.completed":
            # Acknowledge but ignore other events
            self._respond(200, {"ok": True})
            return

        # Extract transaction details
        data           = event.get("data", {})
        transaction_id = data.get("id", "")
        customer_id    = data.get("customer_id", "")

        # Paddle Billing puts customer_id in the transaction, not the email.
        # We need to call the Paddle API to get the customer email.
        email = ""
        if customer_id:
            email = self._get_customer_email(customer_id)

        if not email:
            print(f"Could not get email for customer {customer_id}")
            self._respond(200, {"ok": True, "note": "no email"})
            return

        # Determine license type from items
        items        = data.get("items", [])
        license_type = None
        for item in items:
            price_id = item.get("price", {}).get("id", "")
            if price_id == PRICE_ANNUAL:
                license_type = "annual"
                break
            elif price_id == PRICE_LIFETIME:
                license_type = "lifetime"
                break

        if not license_type:
            print(f"Unknown price ID in transaction {transaction_id}")
            self._respond(200, {"ok": True, "note": "unknown price"})
            return

        # Generate and send license key
        license_key = generate_license_key(license_type, transaction_id)
        print(f"Generated {license_type} key for {email}: {license_key}")

        success = send_license_email(email, license_key, license_type)
        if success:
            self._respond(200, {"ok": True, "key_sent": True})
        else:
            # Return 200 anyway so Paddle does not retry
            # (retries would send duplicate keys)
            self._respond(200, {"ok": True, "key_sent": False,
                                "error": "email delivery failed"})

    def _get_customer_email(self, customer_id: str) -> str:
        """Fetch customer email from Paddle API."""
        import os as _os
        # Use server-side API key from environment
        api_key = _os.environ.get("PADDLE_API_KEY", "")
        if not api_key:
            # Fall back to client token for read operations
            api_key = "live_f1109cbc87e7e333981ada723f"

        url = f"https://api.paddle.com/customers/{customer_id}"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {api_key}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                email = result.get("data", {}).get("email", "")
                print(f"Customer email fetched: {email}")
                return email
        except Exception as e:
            print(f"Failed to fetch customer email: {e}")
            return ""

    def do_GET(self):
        """Health check endpoint."""
        self._respond(200, {"status": "ok", "service": "wrencher-webhook"})

    def _respond(self, code: int, body: dict):
        response = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, fmt, *args):
        print(fmt % args)