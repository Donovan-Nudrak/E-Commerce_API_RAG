import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.core.redis import get_redis
from app.database.session import get_db
from app.api.v1.auth.dependencies import get_current_customer
from app.models.customer import Customer
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserProfileResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    db: Session = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    service = AuthService(db, redis)
    try:
        customer = await service.register(data)
        return {"message": "Account created successfully.", "customer_id": customer.id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    data: LoginRequest,
    db: Session = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    service = AuthService(db, redis)
    try:
        tokens = await service.login(data)
        return tokens
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    customer: Customer = Depends(get_current_customer),
    redis=Depends(get_redis),
    db: Session = Depends(get_db),
) -> dict:
    service = AuthService(db, redis)
    await service.logout(customer.id)
    return {"message": "Logged out successfully."}


@router.post("/refresh-token")
async def refresh_token(
    data: RefreshRequest,
    db: Session = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    service = AuthService(db, redis)
    try:
        tokens = await service.refresh_token(data.refresh_token)
        return tokens
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=UserProfileResponse)
def me(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    try:
        profile = UserService(db).get_profile(customer.id)
        return UserProfileResponse.from_customer(profile)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    service = AuthService(db, redis)
    await service.forgot_password(data.email)
    return {"message": "If the email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
    redis=Depends(get_redis),
) -> dict:
    service = AuthService(db, redis)
    try:
        await service.reset_password(data.token, data.new_password)
        return {"message": "Password updated successfully."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

