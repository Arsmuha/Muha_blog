from __future__ import annotations

from pydantic import BaseModel, EmailStr, field_validator


class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str
    confirm_password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Имя пользователя должно быть не менее 3 символов")
        if len(v) > 50:
            raise ValueError("Имя пользователя должно быть не более 50 символов")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Пароль должен быть не менее 6 символов")
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm(cls, v: str, info):
        data = info.data
        if "password" in data and v != data["password"]:
            raise ValueError("Пароли не совпадают")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    username: str
    avatar_url: str | None = None
    bio: str | None = None
    role: str

    model_config = {"from_attributes": True}
