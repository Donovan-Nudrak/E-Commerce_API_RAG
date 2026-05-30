from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.order import OrderStatus
from app.schemas.order import OrderItemResponse


class AdminOrderResponse(BaseModel):
    id: int
    customer_id: int
    customer_email: str
    customer_first_name: str
    customer_last_name: str
    payment_method_id: int | None
    total: Decimal
    status: OrderStatus
    items: list[OrderItemResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardRecentOrder(BaseModel):
    id: int
    customer_email: str
    customer_first_name: str
    customer_last_name: str
    total: Decimal
    status: OrderStatus
    created_at: datetime


class DashboardResponse(BaseModel):
    total_customers: int
    total_products_active: int
    total_products_inactive: int
    low_stock_products: int
    total_orders: int
    orders_by_status: dict[str, int]
    total_revenue: Decimal
    recent_orders: list[DashboardRecentOrder]


class CustomerAdminResponse(BaseModel):
    id: int
    role_id: int
    role_name: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerAdminDetailResponse(CustomerAdminResponse):
    orders_count: int
    total_spent: Decimal


class CustomerAdminUpdate(BaseModel):
    role_id: int | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
