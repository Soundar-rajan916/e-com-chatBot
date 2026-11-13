import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

# Precomputed dummy hash for timing-attack resistance
DUMMY_PASSWORD_HASH = ph.hash("dummy_constant_time_comparison_password")


def hash_password(password: str) -> str:
    """Hashes a password using Argon2id."""
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifies a password against an Argon2id hash."""
    try:
        return ph.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, Exception):
        return False


def dummy_verify_password(password: str) -> bool:
    """Runs a constant-time dummy verification when email is not found."""
    try:
        ph.verify(DUMMY_PASSWORD_HASH, password)
    except Exception:
        pass
    return False


def generate_session_token() -> str:
    """Generates an opaque cryptographic session token."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Computes the SHA-256 hex digest of an opaque session token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
