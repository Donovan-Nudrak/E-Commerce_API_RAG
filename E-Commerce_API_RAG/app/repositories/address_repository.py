from sqlalchemy.orm import Session

from app.models.address import Address


class AddressRepository:

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_by_customer(self, customer_id: int) -> list[Address]:
        return (
            self.db.query(Address)
            .filter(Address.customer_id == customer_id)
            .order_by(Address.id)
            .all()
        )

    def get_by_id(self, address_id: int) -> Address | None:
        return self.db.query(Address).filter(Address.id == address_id).first()

    def create(self, address: Address) -> Address:
        self.db.add(address)
        self.db.commit()
        self.db.refresh(address)
        return address

    def update(self, address: Address) -> Address:
        self.db.commit()
        self.db.refresh(address)
        return address

    def delete(self, address: Address) -> None:
        self.db.delete(address)
        self.db.commit()
