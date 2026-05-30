from pydantic import BaseModel, EmailStr

from app.models.customer import Customer


class UserProfileResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    role: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_customer(cls, customer: Customer) -> "UserProfileResponse":
        return cls(
            id=customer.id,
            email=customer.email,
            first_name=customer.first_name,
            last_name=customer.last_name,
            phone=customer.phone,
            role=customer.role.name,
        )


class UserProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
