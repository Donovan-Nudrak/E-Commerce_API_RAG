from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, OrderStatus


class OrderRepository:

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_by_customer(self, customer_id: int) -> list[Order]:
        return (
            self.db.query(Order)
            .filter(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_by_id(self, order_id: int) -> Order | None:
        return self.db.query(Order).filter(Order.id == order_id).first()

    def get_by_id_admin(self, order_id: int) -> Order | None:
        return (
            self.db.query(Order)
            .options(joinedload(Order.items), joinedload(Order.customer))
            .filter(Order.id == order_id)
            .first()
        )

    def get_all_admin(
        self,
        skip: int = 0,
        limit: int = 20,
        status: OrderStatus | None = None,
    ) -> list[Order]:
        query = (
            self.db.query(Order)
            .options(joinedload(Order.items), joinedload(Order.customer))
            .order_by(Order.created_at.desc())
        )
        if status is not None:
            query = query.filter(Order.status == status)
        return query.offset(skip).limit(limit).all()

    def count_all(self) -> int:
        return self.db.query(func.count(Order.id)).scalar() or 0

    def count_by_status(self) -> dict[str, int]:
        rows = (
            self.db.query(Order.status, func.count(Order.id))
            .group_by(Order.status)
            .all()
        )
        return {status.value: count for status, count in rows}

    def sum_revenue(self) -> Decimal:
        result = (
            self.db.query(func.coalesce(func.sum(Order.total), 0))
            .filter(
                Order.status.in_(
                    [OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED]
                )
            )
            .scalar()
        )
        return Decimal(str(result))

    def get_recent(self, limit: int = 10) -> list[Order]:
        return (
            self.db.query(Order)
            .options(joinedload(Order.customer))
            .order_by(Order.created_at.desc())
            .limit(limit)
            .all()
        )

    def create(self, order: Order) -> Order:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def update(self, order: Order) -> Order:
        self.db.commit()
        self.db.refresh(order)
        return order
