from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PaymentType(Base):
    __tablename__ = "payment_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # Relationships
    user_payment_methods: Mapped[list["UserPaymentMethod"]] = relationship(
        back_populates="payment_type"
    )
