from sqlalchemy.orm import Session

from app.models.payment_type import PaymentType
from app.repositories.payment_type_repository import PaymentTypeRepository


class PaymentTypeService:

    def __init__(self, db: Session) -> None:
        self.repo = PaymentTypeRepository(db)

    def list_types(self, domain_only: bool = False) -> list[PaymentType]:
        return self.repo.get_all(domain_only=domain_only)
