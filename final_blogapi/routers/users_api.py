from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.session import get_db
from models.db_models import User
from routers.deps import get_current_user, require_role
from schemas.users import UserPublic, UserUpdate
from services import subscription_service, user_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserPublic)
def update_me(payload: UserUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # uniqueness checks
    if payload.email and payload.email != user.email and user_service.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already exists")
    if payload.username and payload.username != user.username and user_service.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="Username already exists")

    user = user_service.update_user(
        db,
        user=user,
        email=payload.email,
        username=payload.username,
        bio=payload.bio,
        avatar_url=payload.avatar_url,
    )
    return user


@router.get("", response_model=list[UserPublic])
def list_users(
    q: str | None = Query(None, description="search query"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * per_page
    if q:
        return user_service.search_users(db, q=q, limit=per_page, offset=offset)
    return db.query(User).order_by(User.id.desc()).offset(offset).limit(per_page).all()


@router.get("/{user_id}", response_model=UserPublic)
def get_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u


@router.post("/{user_id}/follow")
def toggle_follow(
    user_id: int,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    if me.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    state = subscription_service.toggle_subscription(db, subscriber_id=me.id, target_user_id=user_id)
    return {"following": state}


@router.delete("/{user_id}", dependencies=[Depends(require_role("admin"))])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(u)
    db.commit()
    return {"ok": True}
