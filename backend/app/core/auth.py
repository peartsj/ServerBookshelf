import base64
import hashlib
import hmac
import json
import secrets
import time

from app.core.config import settings


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def generate_password_salt() -> str:
    return secrets.token_hex(16)


def hash_password(password: str, salt: str) -> str:
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    )
    return derived.hex()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    expected = hash_password(password, salt)
    return hmac.compare_digest(expected, password_hash)


def create_access_token(username: str) -> str:
    expires_at = int(time.time()) + settings.auth_token_ttl_hours * 3600
    payload = {"sub": username, "exp": expires_at}

    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        settings.auth_secret.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"{encoded_payload}.{signature}"


def decode_access_token(token: str) -> str:
    try:
        encoded_payload, provided_signature = token.split(".", maxsplit=1)
    except ValueError as exc:
        raise ValueError("Malformed token") from exc

    expected_signature = hmac.new(
        settings.auth_secret.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(provided_signature, expected_signature):
        raise ValueError("Invalid token signature")

    try:
        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid token payload") from exc

    exp = payload.get("exp")
    subject = payload.get("sub")

    if not isinstance(exp, int) or exp < int(time.time()):
        raise ValueError("Token expired")
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("Token subject missing")

    return subject.strip().lower()
