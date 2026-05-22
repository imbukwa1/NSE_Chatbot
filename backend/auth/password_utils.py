from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a raw password before storing it."""
    return pwd_context.hash(password)


def verify_password(raw_password: str, hashed_password: str) -> bool:
    """Verify a raw password against a stored hash."""
    return pwd_context.verify(raw_password, hashed_password)

