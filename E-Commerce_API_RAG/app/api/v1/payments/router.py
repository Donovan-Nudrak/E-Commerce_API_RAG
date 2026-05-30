from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.auth.dependencies import get_current_customer
from app.database.session import get_db
from app.models.customer import Customer
from app.schemas.payment import PaymentMethodCreate, PaymentMethodResponse
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("/methods", response_model=list[PaymentMethodResponse])
def get_methods(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> list[PaymentMethodResponse]:
    return PaymentService(db).get_methods(customer.id)


@router.post(
    "/methods",
    response_model=PaymentMethodResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_method(
    data: PaymentMethodCreate,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> PaymentMethodResponse:
    return PaymentService(db).add_method(customer.id, data)


@router.delete("/methods/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_method(
    method_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> None:
    try:
        PaymentService(db).delete_method(customer.id, method_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
