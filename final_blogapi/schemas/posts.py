from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, field_validator


class PostCreate(BaseModel):
    title: str
    content: str
    status: str = "draft"
    category_ids: list[int] = []

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Заголовок слишком короткий")
        if len(v) > 500:
            raise ValueError("Заголовок слишком длинный")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("draft", "published", "archived"):
            raise ValueError("Неверный статус")
        return v


class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: str | None = None
    category_ids: list[int] | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ("draft", "published", "archived"):
            raise ValueError("Неверный статус")
        return v


class PostResponse(BaseModel):
    id: int
    author_id: int
    title: str
    content: str
    excerpt: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    view_count: int
    likes: int = 0
    dislikes: int = 0
    favorites: int = 0
    categories: list[dict] = []
    author_username: str | None = None

    model_config = {"from_attributes": True}
