from sqlalchemy.orm import Session

from app.models.address import Address
from app.repositories.address_repository import AddressRepository
from app.schemas.address import AddressCreate, AddressUpdate


class AddressService:

    def __init__(self, db: Session) -> None:
        self.repo = AddressRepository(db)

    def list_for_customer(self, customer_id: int) -> list[Address]:
        return self.repo.get_all_by_customer(customer_id)

    def get_for_customer(self, address_id: int, customer_id: int) -> Address:
        address = self.repo.get_by_id(address_id)

        if not address or address.customer_id != customer_id:
            raise ValueError("Address not found.")

        return address

    def create(self, customer_id: int, data: AddressCreate) -> Address:
        address = Address(
            customer_id=customer_id,
            street=data.street,
            city=data.city,
            state=data.state,
            postal_code=data.postal_code,
            country=data.country,
        )
        return self.repo.create(address)

    def update(
        self, address_id: int, customer_id: int, data: AddressUpdate
    ) -> Address:
        address = self.get_for_customer(address_id, customer_id)

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(address, field, value)

        return self.repo.update(address)

    def delete(self, address_id: int, customer_id: int) -> None:
        address = self.get_for_customer(address_id, customer_id)
        self.repo.delete(address)
