from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, field_validator


class CommentCreate(BaseModel):
    content: str
    parent_comment_id: int | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Комментарий не может быть пустым")
        if len(v) > 5000:
            raise ValueError("Комментарий слишком длинный")
        return v


class CommentResponse(BaseModel):
    id: int
    post_id: int
    author_id: int
    content: str
    created_at: datetime
    parent_comment_id: int | None = None
    author_username: str | None = None

    model_config = {"from_attributes": True}
