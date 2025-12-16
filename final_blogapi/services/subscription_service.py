from __future__ import annotations

from sqlalchemy.orm import Session

from models.db_models import Subscription


def is_subscribed(db: Session, *, subscriber_id: int, target_user_id: int) -> bool:
    return (
        db.get(Subscription, {"subscriber_id": subscriber_id, "target_user_id": target_user_id})
        is not None
    )


def toggle_subscription(db: Session, *, subscriber_id: int, target_user_id: int) -> bool:
    existing = db.get(
        Subscription, {"subscriber_id": subscriber_id, "target_user_id": target_user_id}
    )
    if existing:
        db.delete(existing)
        db.commit()
        return False
    db.add(Subscription(subscriber_id=subscriber_id, target_user_id=target_user_id))
    db.commit()
    return True
