from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database.session import get_db
from schemas.auth import UserLogin, UserRegister, UserResponse
from services import user_service
from services.auth_service import create_access_token, get_password_hash, verify_password

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")


def _set_auth_cookie(resp, token: str):
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 7,  # 7 days
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.post("/register", response_class=HTMLResponse)
async def register_user(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    try:
        data = UserRegister(
            email=form.get("email", ""),
            username=form.get("username", ""),
            password=form.get("password", ""),
            confirm_password=form.get("confirm_password", ""),
        )
    except Exception as e:
        return templates.TemplateResponse("auth/register.html", {"request": request, "error": str(e)})

    if user_service.get_user_by_email(db, data.email):
        return templates.TemplateResponse(
            "auth/register.html", {"request": request, "error": "Пользователь с таким email уже существует"}
        )
    if user_service.get_user_by_username(db, data.username):
        return templates.TemplateResponse(
            "auth/register.html", {"request": request, "error": "Пользователь с таким именем уже существует"}
        )

    user = user_service.create_user(db, email=data.email, username=data.username, password_hash=get_password_hash(data.password))

    token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})
    resp = RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    _set_auth_cookie(resp, token)
    return resp


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login", response_class=HTMLResponse)
async def login_user(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    try:
        data = UserLogin(email=form.get("email", ""), password=form.get("password", ""))
    except Exception as e:
        return templates.TemplateResponse("auth/login.html", {"request": request, "error": str(e)})

    user = user_service.get_user_by_email(db, data.email)
    if not user or not verify_password(data.password, user.password_hash):
        return templates.TemplateResponse(
            "auth/login.html", {"request": request, "error": "Неверный email или пароль"}
        )

    token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})
    resp = RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    _set_auth_cookie(resp, token)
    return resp


@router.get("/logout")
async def logout():
    resp = RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    resp.delete_cookie("access_token")
    return resp


# JSON API for auth (optional)
@router.post("/api/auth/login", response_model=UserResponse)
def api_login(payload: UserLogin, db: Session = Depends(get_db)):
    user = user_service.get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})
    token = create_access_token({"sub": str(user.id), "username": user.username, "role": user.role})
    resp = JSONResponse(UserResponse.model_validate(user).model_dump())
    _set_auth_cookie(resp, token)
    return resp
