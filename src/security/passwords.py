from anyio import CapacityLimiter, to_thread
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


_password_limiter = CapacityLimiter(4)


async def hash_password_async(password: str) -> str:
    return await to_thread.run_sync(hash_password, password, limiter=_password_limiter)


async def verify_password_async(password: str, password_hash: str) -> bool:
    return await to_thread.run_sync(
        verify_password, password, password_hash, limiter=_password_limiter
    )
