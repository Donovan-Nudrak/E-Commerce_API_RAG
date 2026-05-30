from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.payment_type import PaymentTypeResponse
from app.services.payment_type_service import PaymentTypeService

router = APIRouter(prefix="/payment-types", tags=["Payment Types"])


@router.get("/", response_model=list[PaymentTypeResponse])
def list_payment_types(
    domain_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[PaymentTypeResponse]:
    return PaymentTypeService(db).list_types(domain_only=domain_only)
