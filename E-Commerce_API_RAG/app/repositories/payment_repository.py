from sqlalchemy.orm import Session

from app.models.user_payment_method import UserPaymentMethod


class PaymentRepository:

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_by_customer(self, customer_id: int) -> list[UserPaymentMethod]:
        return (
            self.db.query(UserPaymentMethod)
            .filter(UserPaymentMethod.customer_id == customer_id)
            .all()
        )

    def get_by_id(self, method_id: int) -> UserPaymentMethod | None:
        return (
            self.db.query(UserPaymentMethod)
            .filter(UserPaymentMethod.id == method_id)
            .first()
        )

    def create(self, method: UserPaymentMethod) -> UserPaymentMethod:
        self.db.add(method)
        self.db.commit()
        self.db.refresh(method)
        return method

    def delete(self, method: UserPaymentMethod) -> None:
        self.db.delete(method)
        self.db.commit()
