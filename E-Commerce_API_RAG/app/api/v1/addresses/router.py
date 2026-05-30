from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.auth.dependencies import get_current_customer
from app.database.session import get_db
from app.models.customer import Customer
from app.schemas.address import AddressCreate, AddressResponse, AddressUpdate
from app.services.address_service import AddressService

router = APIRouter(prefix="/addresses", tags=["Addresses"])


@router.get("/", response_model=list[AddressResponse])
def list_addresses(
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> list[AddressResponse]:
    return AddressService(db).list_for_customer(customer.id)


@router.post("/", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
def create_address(
    data: AddressCreate,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> AddressResponse:
    return AddressService(db).create(customer.id, data)


@router.get("/{address_id}", response_model=AddressResponse)
def get_address(
    address_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> AddressResponse:
    try:
        return AddressService(db).get_for_customer(address_id, customer.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: int,
    data: AddressUpdate,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> AddressResponse:
    try:
        return AddressService(db).update(address_id, customer.id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: int,
    customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> None:
    try:
        AddressService(db).delete(address_id, customer.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
