import logging
from datetime import timedelta

import redis.asyncio as redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.customer import Customer
from app.repositories.customer_repository import CustomerRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.auth import LoginRequest, RegisterRequest
from app.utils.email import send_reset_password_email


logger = logging.getLogger(__name__)

REFRESH_TOKEN_PREFIX = "refresh:"
RESET_TOKEN_PREFIX = "reset:"


class AuthService:

    def __init__(self, db: Session, redis: redis.Redis) -> None:
        self.db = db
        self.redis = redis
        self.customer_repo = CustomerRepository(db)
        self.role_repo = RoleRepository(db)

    async def register(self, data: RegisterRequest) -> Customer:
        existing = self.customer_repo.get_by_email(data.email)
        if existing:
            raise ValueError("Email already registered.")

        customer_role = self.role_repo.get_by_name("Customer")

        customer = Customer(
            role_id=customer_role.id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone=data.phone,
            password_hash=hash_password(data.password),
        )

        return self.customer_repo.create(customer)

    async def login(self, data: LoginRequest) -> dict:
        customer = self.customer_repo.get_by_email(data.email)

        if not customer or not verify_password(data.password, customer.password_hash):
            raise ValueError("Invalid email or password.")

        access_token = create_access_token(str(customer.id))
        refresh_token = create_refresh_token(str(customer.id))

        await self.redis.setex(
            f"{REFRESH_TOKEN_PREFIX}{customer.id}",
            timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            refresh_token,
        )

        return {"access_token": access_token, "refresh_token": refresh_token}

    async def logout(self, customer_id: int) -> None:
        await self.redis.delete(f"{REFRESH_TOKEN_PREFIX}{customer_id}")

    async def refresh_token(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token)

        if not payload or payload.get("type") != "refresh":
            raise ValueError("Invalid refresh token.")

        customer_id = payload.get("sub")
        stored_token = await self.redis.get(f"{REFRESH_TOKEN_PREFIX}{customer_id}")

        if not stored_token or stored_token != refresh_token:
            raise ValueError("Refresh token expired or invalid.")

        access_token = create_access_token(customer_id)
        return {"access_token": access_token}


    async def forgot_password(self, email: str) -> None:
        customer = self.customer_repo.get_by_email(email)

        if not customer:
            # No revelamos si el email existe o no por seguridad
            return

        reset_token = create_access_token(str(customer.id))

        await self.redis.setex(
            f"{RESET_TOKEN_PREFIX}{customer.id}",
            timedelta(minutes=30),
            reset_token,
        )

        await send_reset_password_email(customer.email, reset_token)


    async def reset_password(self, token: str, new_password: str) -> None:
        payload = decode_token(token)

        if not payload:
            raise ValueError("Invalid or expired token.")

        customer_id = int(payload.get("sub"))
        stored_token = await self.redis.get(f"{RESET_TOKEN_PREFIX}{customer_id}")

        if not stored_token or stored_token != token:
            raise ValueError("Token expired or already used.")

        customer = self.customer_repo.get_by_id(customer_id)
        customer.password_hash = hash_password(new_password)
        self.customer_repo.update(customer)

        await self.redis.delete(f"{RESET_TOKEN_PREFIX}{customer_id}")
