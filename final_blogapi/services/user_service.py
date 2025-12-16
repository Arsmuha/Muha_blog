from __future__ import annotations

from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.db_models import User
from services.search_cache import users_search_cache


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, *, email: str, username: str, password_hash: str) -> User:
    user = User(email=email, username=username, password_hash=password_hash, role="user", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    users_search_cache.clear()
    return user


def update_user(
    db: Session,
    *,
    user: User,
    email: str | None = None,
    username: str | None = None,
    bio: str | None = None,
    avatar_url: str | None = None,
) -> User:
    if email is not None:
        user.email = email
    if username is not None:
        user.username = username
    if bio is not None:
        user.bio = bio
    if avatar_url is not None:
        user.avatar_url = avatar_url
    db.commit()
    db.refresh(user)
    users_search_cache.clear()
    return user


def search_users(db: Session, q: str, limit: int = 20, offset: int = 0) -> list[User]:
    key = f"{q.strip().lower()}|{limit}|{offset}"
    if key in users_search_cache:
        ids = users_search_cache[key]
        if not ids:
            return []
        return list(db.query(User).filter(User.id.in_(ids)).all())

    q_like = f"%{q.strip()}%"
    users = (
        db.query(User)
        .filter(or_(User.username.ilike(q_like), User.email.ilike(q_like)))
        .order_by(User.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    users_search_cache[key] = [u.id for u in users]
    return users
