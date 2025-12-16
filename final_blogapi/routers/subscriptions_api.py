from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.session import get_db
from models.db_models import Subscription, User
from routers.deps import get_current_user

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("/me")
def my_subscriptions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(User)
        .join(Subscription, Subscription.target_user_id == User.id)
        .filter(Subscription.subscriber_id == user.id)
        .order_by(Subscription.subscribed_at.desc())
        .all()
    )
    return [{"id": u.id, "username": u.username, "avatar_url": u.avatar_url} for u in rows]
