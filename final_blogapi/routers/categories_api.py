from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from models.db_models import Category
from routers.deps import require_role
from schemas.categories import CategoryCreate, CategoryResponse
from services.category_service import list_categories

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return list_categories(db)


@router.post("", response_model=CategoryResponse, dependencies=[Depends(require_role("admin", "moderator"))])
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    if db.query(Category).filter(Category.slug == payload.slug).first():
        raise HTTPException(status_code=400, detail="slug already exists")
    if db.query(Category).filter(Category.name == payload.name).first():
        raise HTTPException(status_code=400, detail="name already exists")
    c = Category(name=payload.name, slug=payload.slug, description=payload.description, color=payload.color)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{category_id}", dependencies=[Depends(require_role("admin"))])
def delete_category(category_id: int, db: Session = Depends(get_db)):
    c = db.get(Category, category_id)
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(c)
    db.commit()
    return {"ok": True}
