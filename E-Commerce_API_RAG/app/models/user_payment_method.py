from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.base import TimestampMixin


class UserPaymentMethod(Base, TimestampMixin):
    __tablename__ = "user_payment_methods"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    payment_type_id: Mapped[int] = mapped_column(
        ForeignKey("payment_types.id"), nullable=False
    )
    reference: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="payment_methods")
    payment_type: Mapped["PaymentType"] = relationship(
        back_populates="user_payment_methods"
    )
