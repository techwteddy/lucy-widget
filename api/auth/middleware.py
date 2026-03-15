from dataclasses import dataclass
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from api.config import settings

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    sub: str  # Supabase user UUID
    email: str
    role: str = "authenticated"


def _decode_token(token: str) -> CurrentUser:
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub = payload.get("sub")
    email = payload.get("email", "")
    role = payload.get("role", "authenticated")

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(sub=sub, email=email, role=role)


DEMO_USER = CurrentUser(sub="demo-user-id", email="demo@example.com", role="authenticated")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> CurrentUser:
    if settings.demo_mode:
        if not credentials or credentials.credentials == "demo-token":
            return DEMO_USER
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_token(credentials.credentials)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[CurrentUser]:
    """Returns CurrentUser if token present, None otherwise (for admin-key routes)."""
    if not credentials:
        return None
    return _decode_token(credentials.credentials)
