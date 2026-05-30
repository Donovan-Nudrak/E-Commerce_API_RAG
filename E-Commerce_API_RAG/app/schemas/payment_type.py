from pydantic import BaseModel


class PaymentTypeResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}
