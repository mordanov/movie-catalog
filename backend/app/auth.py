from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Header, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def _users() -> dict[str, str]:
    """Return {login: hash} for all configured web users."""
    s = get_settings()
    users: dict[str, str] = {}
    if s.web_user_1_login and s.web_user_1_password_hash:
        users[s.web_user_1_login] = s.web_user_1_password_hash
    if s.web_user_2_login and s.web_user_2_password_hash:
        users[s.web_user_2_login] = s.web_user_2_password_hash
    return users


def authenticate_user(login: str, password: str) -> str | None:
    """Return login if valid, else None."""
    users = _users()
    hashed = users.get(login)
    if hashed and verify_password(password, hashed):
        return login
    return None


def create_access_token(login: str) -> str:
    s = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=s.jwt_expire_hours)
    return jwt.encode({"sub": login, "exp": expire}, s.jwt_secret, algorithm="HS256")


def get_current_user(
    access_token: str | None = Cookie(default=None),
    x_bot_secret: str | None = Header(default=None),
) -> str:
    s = get_settings()
    # Bot internal access via shared secret
    if x_bot_secret and s.bot_secret and x_bot_secret == s.bot_secret:
        return "bot"
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(access_token, s.jwt_secret, algorithms=["HS256"])
        login: str = payload.get("sub", "")
        if not login:
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return login
