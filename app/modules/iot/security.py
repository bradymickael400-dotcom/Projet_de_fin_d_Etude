"""Helpers de securite pour les identites ESP32."""

import hashlib
import hmac
import secrets


def generate_secret(byte_count=32):
    return secrets.token_urlsafe(byte_count)


def hash_secret(secret):
    if not secret:
        raise ValueError("Secret requis")
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def verify_secret(raw_secret, stored_hash):
    if not raw_secret or not stored_hash:
        return False
    return hmac.compare_digest(hash_secret(raw_secret), stored_hash)
