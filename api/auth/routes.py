import httpx
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from api.config import settings
from .middleware import get_current_user, CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


async def _supabase_auth(endpoint: str, payload: dict) -> dict:
    """Call Supabase Auth REST API."""
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service not configured",
        )
    url = f"{settings.supabase_url}/auth/v1/{endpoint}"
    headers = {"apikey": settings.supabase_service_role_key, "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code >= 400:
        detail = resp.json().get("error_description") or resp.json().get("msg") or "Auth error"
        raise HTTPException(status_code=resp.status_code, detail=detail)
    return resp.json()


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: AuthRequest):
    data = await _supabase_auth("signup", {"email": body.email, "password": body.password})
    session = data.get("session") or {}
    user = data.get("user") or {}
    return AuthResponse(
        access_token=session.get("access_token", ""),
        user_id=user.get("id", ""),
        email=user.get("email", body.email),
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: AuthRequest):
    data = await _supabase_auth(
        "token?grant_type=password",
        {"email": body.email, "password": body.password},
    )
    return AuthResponse(
        access_token=data.get("access_token", ""),
        user_id=data.get("user", {}).get("id", ""),
        email=data.get("user", {}).get("email", body.email),
    )


@router.get("/me")
async def me(user: CurrentUser = Depends(get_current_user)):
    return {"sub": user.sub, "email": user.email, "role": user.role}


@router.post("/demo-login", response_model=AuthResponse)
async def demo_login():
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return AuthResponse(
        access_token="demo-token",
        user_id="demo-user-id",
        email="demo@example.com",
    )
