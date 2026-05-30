from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.auth.dependencies import get_current_customer
from app.database.session import get_db
from app.models.customer import Customer
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartResponse
from app.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("/", response_model=CartResponse)
def get_cart(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> CartResponse:
    return CartService(db).get_cart(customer.id)


@router.post("/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
def add_item(
    data: CartItemAdd,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> CartResponse:
    try:
        return CartService(db).add_item(customer.id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/items/{item_id}", response_model=CartResponse)
def update_item(
    item_id: int,
    data: CartItemUpdate,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> CartResponse:
    try:
        return CartService(db).update_item(customer.id, item_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/items/{item_id}", response_model=CartResponse)
def delete_item(
    item_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> CartResponse:
    try:
        return CartService(db).delete_item(customer.id, item_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> None:
    CartService(db).clear(customer.id)
