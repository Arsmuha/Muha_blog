from __future__ import annotations

from pydantic import BaseModel, field_validator


class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    color: str = "#3498db"

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("slug обязателен")
        if " " in v:
            raise ValueError("slug не должен содержать пробелы")
        return v


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    color: str

    model_config = {"from_attributes": True}
