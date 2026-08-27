"""
Security and Cryptography Module.
Implements PBKDF2-HMAC password hashing with cryptographically secure random salts.
"""

import getpass
import hashlib
import hmac
import os
import sys
from config import PASSWORD_HASH_ITERATIONS, PASSWORD_SALT_BYTES


def generate_salt() -> bytes:
    """Generate cryptographically secure random salt."""
    return os.urandom(PASSWORD_SALT_BYTES)


def hash_password(password: str, salt: bytes = None) -> tuple[str, str]:
    """
    Hash a password using PBKDF2-HMAC-SHA256.
    Returns:
        tuple[str, str]: (password_hash_hex, salt_hex)
    """
    if salt is None:
        salt = generate_salt()
    
    pwd_bytes = password.encode("utf-8")
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        pwd_bytes,
        salt,
        PASSWORD_HASH_ITERATIONS
    )
    return hash_bytes.hex(), salt.hex()


def verify_password(plain_password: str, stored_hash_hex: str, salt_hex: str) -> bool:
    """
    Verify a plain password against the stored hash and salt.
    Uses hmac.compare_digest for constant-time comparison.
    """
    try:
        salt_bytes = bytes.fromhex(salt_hex)
        computed_hash_hex, _ = hash_password(plain_password, salt_bytes)
        return hmac.compare_digest(computed_hash_hex, stored_hash_hex)
    except (ValueError, TypeError):
        return False


def get_secure_password(prompt: str = "Enter password: ") -> str:
    """
    Prompt user for password with hidden input using getpass.
    Gracefully falls back to input() if getpass is unsupported in the current stream.
    """
    try:
        pwd = getpass.getpass(prompt)
        return pwd
    except Exception:
        # Fallback for environments where getpass fails
        return input(prompt)
