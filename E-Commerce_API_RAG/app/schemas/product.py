from decimal import Decimal

from pydantic import BaseModel, field_validator


class ProductCreate(BaseModel):
    category_id: int
    name: str
    description: str | None = None
    barcode: str | None = None
    price: Decimal
    discount_price: Decimal | None = None
    stock: int = 0

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Price must be greater than zero.")
        return value

    @field_validator("discount_price")
    @classmethod
    def discount_must_be_less_than_price(
        cls, value: Decimal | None, info
    ) -> Decimal | None:
        if value is not None and "price" in info.data:
            if value >= info.data["price"]:
                raise ValueError("Discount price must be less than the original price.")
        return value

    @field_validator("stock")
    @classmethod
    def stock_must_be_positive(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Stock cannot be negative.")
        return value


class ProductUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = None
    description: str | None = None
    barcode: str | None = None
    price: Decimal | None = None
    discount_price: Decimal | None = None
    stock: int | None = None
    is_active: bool | None = None

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value <= 0:
            raise ValueError("Price must be greater than zero.")
        return value

    @field_validator("stock")
    @classmethod
    def stock_must_be_positive(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("Stock cannot be negative.")
        return value


class ProductResponse(BaseModel):
    id: int
    category_id: int
    name: str
    description: str | None
    barcode: str | None
    price: Decimal
    discount_price: Decimal | None
    stock: int
    is_active: bool
    image_url: str | None

    model_config = {"from_attributes": True}
