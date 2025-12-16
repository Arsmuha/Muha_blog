from __future__ import annotations

from sqlalchemy.orm import Session

from models.db_models import Category


def list_categories(db: Session) -> list[Category]:
    return db.query(Category).order_by(Category.name.asc()).all()
