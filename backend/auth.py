"""Auth helpers for PetCare Companion.

Password hashing: PBKDF2-HMAC-SHA256 (stdlib hashlib, no extra deps).
Session: signed cookie via itsdangerous.
"""
import hashlib
import hmac
import os
import secrets

from itsdangerous import BadSignature, URLSafeTimedSerializer

# --- Secret key (persist across restarts in a file next to the DB) ---
SECRET_FILE = os.path.join(os.path.dirname(__file__), ".secret_key")
if os.path.exists(SECRET_FILE):
    with open(SECRET_FILE) as f:
        SECRET_KEY = f.read().strip()
else:
    SECRET_KEY = secrets.token_hex(32)
    with open(SECRET_FILE, "w") as f:
        f.write(SECRET_KEY)
    os.chmod(SECRET_FILE, 0o600)

serializer = URLSafeTimedSerializer(SECRET_KEY, salt="petcare-session")

# --- Password hashing (PBKDF2-HMAC-SHA256) ---
_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_hex, dk_hex = stored.split("$")
        iterations = int(iterations)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(dk_hex)
    except (ValueError, AttributeError):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return hmac.compare_digest(dk, expected)


# --- Session cookie ---
SESSION_COOKIE = "petcare_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def create_session_token() -> str:
    return serializer.dumps({"user": "owner"})


def read_session_token(token: str):
    """Return the payload dict if valid, else None."""
    try:
        payload = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return payload
    except BadSignature:
        return None
