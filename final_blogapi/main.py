from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
except Exception:  # pragma: no cover
    Instrumentator = None

from database.init_db import init_db
from routers import (
    auth_router,
    categories_api_router,
    html_router,
    posts_api_router,
    subscriptions_api_router,
    users_api_router,
    ws_router,
)
from services.auth_service import verify_token
from prometheus_fastapi_instrumentator import Instrumentator
instrumentator = Instrumentator()


app = FastAPI(
    title="Blog Platform",
    description="Платформа для ведения блога (FastAPI + Jinja + SQLite)",
    version="2.0.0",
)

# Static
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")



instrumentator.instrument(app)
instrumentator.expose(app)
@app.on_event("startup")
async def _startup():
    init_db()

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    token = request.cookies.get("access_token")
    request.state.is_authenticated = False
    request.state.user_id = None
    request.state.username = None
    request.state.role = None

    if token:
        payload = verify_token(token)
        if payload:
            request.state.is_authenticated = True
            request.state.user_id = payload.get("sub")
            request.state.username = payload.get("username")
            request.state.role = payload.get("role")

    response = await call_next(request)
    return response


# Routers
app.include_router(auth_router)
app.include_router(users_api_router)
app.include_router(posts_api_router)
app.include_router(categories_api_router)
app.include_router(subscriptions_api_router)
app.include_router(html_router)
app.include_router(ws_router)


@app.get("/protected")
async def protected(request: Request):
    if not request.state.is_authenticated:
        return RedirectResponse("/login")
    return {"message": f"Привет, {request.state.username}!"}
