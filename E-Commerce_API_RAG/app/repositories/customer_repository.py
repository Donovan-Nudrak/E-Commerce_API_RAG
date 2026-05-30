from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.address import Address
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.user_payment_method import UserPaymentMethod


class CustomerRepository:

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> Customer | None:
        return self.db.query(Customer).filter(Customer.email == email).first()

    def get_by_id(self, customer_id: int) -> Customer | None:
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def create(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def update(self, customer: Customer) -> Customer:
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def get_all_admin(
        self,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> list[Customer]:
        query = (
            self.db.query(Customer)
            .options(joinedload(Customer.role))
            .order_by(Customer.created_at.desc())
        )
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    Customer.email.ilike(term),
                    Customer.first_name.ilike(term),
                    Customer.last_name.ilike(term),
                )
            )
        return query.offset(skip).limit(limit).all()

    def get_by_id_with_role(self, customer_id: int) -> Customer | None:
        return (
            self.db.query(Customer)
            .options(joinedload(Customer.role))
            .filter(Customer.id == customer_id)
            .first()
        )

    def count_all(self) -> int:
        return self.db.query(func.count(Customer.id)).scalar() or 0

    def get_orders_stats(self, customer_id: int) -> tuple[int, Decimal]:
        orders_count = (
            self.db.query(func.count(Order.id))
            .filter(Order.customer_id == customer_id)
            .scalar()
            or 0
        )
        total_spent = (
            self.db.query(func.coalesce(func.sum(Order.total), 0))
            .filter(
                Order.customer_id == customer_id,
                Order.status.in_(
                    [OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.DELIVERED]
                ),
            )
            .scalar()
        )
        return orders_count, Decimal(str(total_spent))

    def count_admins(self) -> int:
        from app.models.role import Role

        return (
            self.db.query(func.count(Customer.id))
            .join(Role)
            .filter(Role.name == "Administrator")
            .scalar()
            or 0
        )

    def delete(self, customer: Customer) -> None:
        orders_count = (
            self.db.query(func.count(Order.id))
            .filter(Order.customer_id == customer.id)
            .scalar()
            or 0
        )
        if orders_count > 0:
            raise ValueError("Cannot delete account with order history.")

        cart = self.db.query(Cart).filter(Cart.customer_id == customer.id).first()
        if cart:
            self.db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
            self.db.delete(cart)

        self.db.query(Address).filter(Address.customer_id == customer.id).delete()
        self.db.query(UserPaymentMethod).filter(
            UserPaymentMethod.customer_id == customer.id
        ).delete()

        self.db.delete(customer)
        self.db.commit()

