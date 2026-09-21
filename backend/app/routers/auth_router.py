from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.auth import authenticate_user, create_access_token, get_current_user
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    login: str
    password: str


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    login_str = authenticate_user(body.login, body.password)
    if not login_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    token = create_access_token(login_str)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        max_age=60 * 60 * 72,
    )
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


@router.get("/me")
async def me(current_user: str = Depends(get_current_user)):
    return {"login": current_user}
