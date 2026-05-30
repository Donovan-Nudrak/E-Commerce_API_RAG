import logging

from sqlalchemy.orm import Session

from app.models.user_payment_method import UserPaymentMethod
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentMethodCreate

logger = logging.getLogger(__name__)


class PaymentService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PaymentRepository(db)

    def get_methods(self, customer_id: int) -> list[UserPaymentMethod]:
        return self.repo.get_all_by_customer(customer_id)

    def add_method(
        self, customer_id: int, data: PaymentMethodCreate
    ) -> UserPaymentMethod:
        method = UserPaymentMethod(
            customer_id=customer_id,
            payment_type_id=data.payment_type_id,
            reference=data.reference,
        )
        return self.repo.create(method)

    def delete_method(self, customer_id: int, method_id: int) -> None:
        method = self.repo.get_by_id(method_id)

        if not method or method.customer_id != customer_id:
            raise ValueError("Payment method not found.")

        self.repo.delete(method)
