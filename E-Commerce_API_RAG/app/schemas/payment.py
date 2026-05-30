from pydantic import BaseModel


class PaymentMethodCreate(BaseModel):
    payment_type_id: int
    reference: str


class PaymentMethodResponse(BaseModel):
    id: int
    payment_type_id: int
    reference: str

    model_config = {"from_attributes": True}
