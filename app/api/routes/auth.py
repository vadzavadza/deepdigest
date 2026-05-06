from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    MessageResponse, PasswordResetRequest, PasswordResetConfirm,
)
from app.core.security import (
    hash_password, verify_password, create_token,
    create_verification_token, create_password_reset_token, decode_token,
)
from app.services.email import (
    send_verification_email, send_password_reset_email, send_welcome_email,
)
from app.services.notifications import notify_new_user

router = APIRouter()


@router.post("/register", response_model=MessageResponse, status_code=201)
async def register(
    body: RegisterRequest,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Check duplicate
    exists = await db.execute(select(User).where(User.email == body.email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()  # get user.id

    token = create_verification_token(body.email)
    background.add_task(send_verification_email, body.email, token)

    return {"message": "Account created! Check your email to confirm."}


@router.get("/verify")
async def verify_email(token: str, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    from fastapi.responses import RedirectResponse
    try:
        payload = decode_token(token)
    except Exception:
        return RedirectResponse(f"{settings.FRONTEND_URL}/?error=invalid_token")

    if payload.get("type") != "verify":
        return RedirectResponse(f"{settings.FRONTEND_URL}/?error=invalid_token")

    email = payload.get("sub")
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return RedirectResponse(f"{settings.FRONTEND_URL}/?error=not_found")
    if user.is_verified:
        return RedirectResponse(f"{settings.FRONTEND_URL}/?verified=already")

    user.is_verified = True
    background.add_task(send_welcome_email, email)
    if user.telegram_chat_id:
        background.add_task(notify_new_user, user.telegram_chat_id)

    return RedirectResponse(f"{settings.FRONTEND_URL}/?verified=true")


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    user.last_login = datetime.now(timezone.utc)
    token = create_token({"sub": user.email})
    return {"access_token": token}


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: PasswordResetRequest,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    # Always return 200 to prevent email enumeration
    if user:
        token = create_password_reset_token(body.email)
        background.add_task(send_password_reset_email, body.email, token)
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.token)
    if payload.get("type") != "reset":
        raise HTTPException(status_code=400, detail="Invalid token type")

    email = payload.get("sub")
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(body.new_password)
    return {"message": "Password updated successfully"}
