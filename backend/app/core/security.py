from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hasher.verify(password, encoded)
    except UnknownHashError:
        return False


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(claims, SECRET_KEY, algorithm="HS256")


def read_access_token(token: str) -> str | None:
    try:
        claims = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return None
    subject = claims.get("sub")
    return subject if isinstance(subject, str) and subject else None
