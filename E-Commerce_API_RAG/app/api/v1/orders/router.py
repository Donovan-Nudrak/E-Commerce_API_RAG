from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.auth.dependencies import get_current_customer
from app.database.session import get_db
from app.models.customer import Customer
from app.schemas.order import OrderResponse
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> OrderResponse:
    try:
        return OrderService(db).create_from_cart(customer.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=list[OrderResponse])
def get_orders(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> list[OrderResponse]:
    return OrderService(db).get_all(customer.id)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> OrderResponse:
    try:
        return OrderService(db).get_by_id(order_id, customer.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> OrderResponse:
    try:
        return OrderService(db).cancel(order_id, customer.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
