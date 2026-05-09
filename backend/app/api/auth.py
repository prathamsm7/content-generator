"""Account registration and login endpoints."""

from __future__ import annotations

from typing import Annotated

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.store import get_store
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthBody(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=120)


class LoginBody(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _public_user(user: dict) -> dict:
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "display_name": user.get("display_name") or "",
    }


@router.post("/register")
async def register(body: AuthBody) -> dict:
    store = get_store()
    email = _normalize_email(body.email)
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    if store.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = store.create_user(
        email=email,
        password_hash=hash_password(body.password),
        display_name=body.display_name.strip(),
    )
    return {"access_token": create_access_token(user["user_id"]), "user": _public_user(user)}


@router.post("/login")
async def login(body: LoginBody) -> dict:
    store = get_store()
    user = store.get_user_by_email(_normalize_email(body.email))
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return {"access_token": create_access_token(user["user_id"]), "user": _public_user(user)}


@router.get("/me")
async def me(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    return {"user": _public_user(current_user)}
