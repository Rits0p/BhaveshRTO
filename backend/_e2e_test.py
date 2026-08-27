import json
import re
import urllib.request
import urllib.error

BASE = "http://localhost:5000/api"


def call(method, path, data=None, token=None):
    url = BASE + path
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode(errors="replace")


print("1. health:", call("GET", "/health"))
print("2. admin-exists:", call("GET", "/auth/admin-exists"))

status, body = call("POST", "/auth/signup", {"name": "Bhavesh Solanki", "email": "bhavesh@example.com", "password": "SecurePass123"})
print("3. signup:", status, body)

# Second signup must be rejected (single-admin enforcement)
status, body = call("POST", "/auth/signup", {"name": "Someone Else", "email": "other@example.com", "password": "SecurePass123"})
print("3b. second signup (expect 403):", status, body)

status, body = call("POST", "/auth/login", {"email": "bhavesh@example.com", "password": "SecurePass123"})
print("4. login:", status, body)
otp_session_token = body.get("otp_session_token")

with open("backend/_test_server.log", encoding="utf-8", errors="ignore") as f:
    log = f.read()
match = re.findall(r"DEV OTP for bhavesh@example\.com: (\d{6})", log)
otp_code = match[-1] if match else None
print("5. extracted OTP:", otp_code)

status, body = call("POST", "/auth/verify-otp", {"otp_session_token": otp_session_token, "code": "000000"})
print("6a. verify-otp WRONG code (expect 401):", status, body)

status, body = call("POST", "/auth/verify-otp", {"otp_session_token": otp_session_token, "code": otp_code})
print("6b. verify-otp correct code:", status, body.get("success"), "access issued:", bool(body.get("access")))
token = body.get("access")

status, body = call("GET", "/auth/me", token="garbage")
print("7. /auth/me bad token (expect 401):", status, body)

status, body = call("GET", "/auth/me", token=token)
print("8. /auth/me:", status, body)

status, body = call("POST", "/customers", {
    "name": "Test Customer", "contact_number": "+919999999999", "category": "insurance",
    "vehicle_number": "MH12AB1234", "amount_total": "5000.00",
    "start_date": "2026-01-01", "end_date": "2026-08-15",
}, token=token)
print("9. create customer:", status, body)
customer_id = body.get("data", {}).get("id")

# amount_paid must NOT be settable via customer endpoint
status, body = call("PATCH", f"/customers/{customer_id}", {"amount_paid": "9999.00"}, token=token)
print("9b. try to write amount_paid directly (should be ignored):", status, body.get("data", {}).get("amount_paid"))

status, body = call("GET", "/customers?category=fitness_puc", token=token)
print("10. fitness_puc list (field-filtered):", status, "keys of first row (if any):",
      list(body.get("data", [{}])[0].keys()) if body.get("data") else "no rows")

status, body = call("GET", "/customers", token=token)
print("11. list all customers:", status, {"total": body.get("total"), "keys": list(body.get("data", [{}])[0].keys()) if body.get("data") else None})

status, body = call("POST", "/payments", {"customer_id": customer_id, "amount": "1500.00"}, token=token)
print("12. record payment:", status, body)

status, body = call("GET", f"/customers/{customer_id}", token=token)
print("13. customer after payment (amount_paid, amount_pending):", body.get("data", {}).get("amount_paid"), body.get("data", {}).get("amount_pending"))

status, body = call("GET", "/dashboard/summary", token=token)
print("14. dashboard summary:", status, body)

status, body = call("GET", "/dashboard/monthly-collection", token=token)
print("15. monthly collection:", status, body)

status, body = call("GET", "/receipts", token=token)
print("16. overall receipts:", status, body)

status, body = call("GET", f"/receipts/{customer_id}", token=token)
print("17. customer receipt:", status, body)

status, body = call("POST", f"/customers/{customer_id}/send-reminder", token=token)
print("18. send-reminder:", status, body)

status, body = call("GET", "/customers/expiring-soon?category=insurance", token=token)
print("19. expiring-soon:", status, body)

status, body = call("GET", "/customers", token="not.a.valid.token")
print("20. list customers invalid token (expect 401):", status, body)
