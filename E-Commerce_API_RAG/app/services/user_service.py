from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.repositories.customer_repository import CustomerRepository
from app.schemas.user import UserProfileUpdate


class UserService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.customer_repo = CustomerRepository(db)

    def get_profile(self, customer_id: int) -> Customer:
        customer = self.customer_repo.get_by_id_with_role(customer_id)
        if not customer:
            raise ValueError("Customer not found.")
        return customer

    def update_profile(self, customer_id: int, data: UserProfileUpdate) -> Customer:
        customer = self.customer_repo.get_by_id_with_role(customer_id)
        if not customer:
            raise ValueError("Customer not found.")

        updates = data.model_dump(exclude_none=True)
        for field, value in updates.items():
            setattr(customer, field, value)

        return self.customer_repo.update(customer)

    def delete_account(self, customer_id: int) -> None:
        customer = self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise ValueError("Customer not found.")
        self.customer_repo.delete(customer)
