from sqlalchemy.orm import Session

from app.core.constants import DOMAIN_PAYMENT_TYPES
from app.models.payment_type import PaymentType


class PaymentTypeRepository:

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self, domain_only: bool = False) -> list[PaymentType]:
        query = self.db.query(PaymentType).order_by(PaymentType.id)
        if domain_only:
            query = query.filter(PaymentType.name.in_(DOMAIN_PAYMENT_TYPES))
        return query.all()
