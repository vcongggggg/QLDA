from __future__ import annotations

import hashlib
import hmac
import os


_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 260_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), _ITERATIONS)
    return f"{_ALGORITHM}${_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, raw_iterations, salt, expected = password_hash.split("$", 3)
        iterations = int(raw_iterations)
    except (ValueError, TypeError):
        return False
    if algorithm != _ALGORITHM or iterations < 1:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), iterations).hex()
    return hmac.compare_digest(actual, expected)
