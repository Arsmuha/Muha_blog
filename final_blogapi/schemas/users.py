from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    bio: str | None = None
    avatar_url: str | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Имя пользователя должно быть не менее 3 символов")
        if len(v) > 50:
            raise ValueError("Имя пользователя должно быть не более 50 символов")
        return v


class UserPublic(BaseModel):
    id: int
    username: str
    avatar_url: str | None = None
    bio: str | None = None
    role: str

    model_config = {"from_attributes": True}
