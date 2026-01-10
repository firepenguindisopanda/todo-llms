from datetime import datetime, timedelta
from typing import Optional
from app.config import settings

# Try python-jose; fall back to PyJWT if not available
try:
    from jose import jwt  # type: ignore
    from jose.exceptions import JWTError  # type: ignore
except ImportError:
    import jwt  # type: ignore
    JWTError = jwt.PyJWTError  # type: ignore


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": str(subject), "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise
