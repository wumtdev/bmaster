from argon2 import PasswordHasher
from bmaster.api.auth import logger as auth_logger


logger = auth_logger.getChild("hashing")

hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(hash: str, password: str) -> None:
    """Verify password. Raise exception on verification failure."""
    if not hasher.verify(hash, password):
        raise ValueError("Invalid password")


def verify_and_update_password_hash(hash: str, password: str) -> str | None:
    """
    If password matches hash return new hash if hash should be updated.
    Raise exception on verification failure.
    """
    if not hasher.verify(hash, password):
        raise ValueError("Invalid password")

    if hasher.check_needs_rehash(hash):
        return hasher.hash(password)
    else:
        return None
