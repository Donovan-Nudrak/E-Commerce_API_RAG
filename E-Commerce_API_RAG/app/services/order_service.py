from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.repositories.cart_repository import CartRepository
from app.repositories.order_repository import OrderRepository
from app.services.stock_service import StockService


VALID_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.CANCELLED],
    OrderStatus.PAID: [OrderStatus.SHIPPED],
    OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
}


class OrderService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = OrderRepository(db)
        self.cart_repo = CartRepository(db)
        self.stock_service = StockService(db)

    def get_all(self, customer_id: int) -> list[Order]:
        return self.repo.get_all_by_customer(customer_id)

    def get_by_id(self, order_id: int, customer_id: int) -> Order:
        order = self.repo.get_by_id(order_id)

        if not order or order.customer_id != customer_id:
            raise ValueError("Order not found.")

        return order

    def create_from_cart(self, customer_id: int) -> Order:
        cart = self.cart_repo.get_by_customer_id(customer_id)

        if not cart or not cart.items:
            raise ValueError("Cart is empty.")

        for item in cart.items:
            product = item.product
            if not product.is_active:
                raise ValueError(f"Product '{product.name}' is no longer available.")

        self.stock_service.reserve_for_cart_items(cart.items)

        total = Decimal("0")
        order_items = []

        for item in cart.items:
            product = item.product
            unit_price = product.discount_price or product.price
            subtotal = unit_price * item.quantity
            total += subtotal

            order_items.append(
                OrderItem(
                    product_id=product.id,
                    quantity=item.quantity,
                    unit_price=unit_price,
                    subtotal=subtotal,
                )
            )

        order = Order(
            customer_id=customer_id,
            total=total,
            status=OrderStatus.PENDING,
            items=order_items,
        )

        created_order = self.repo.create(order)
        self.cart_repo.clear(cart)

        return created_order

    def cancel(self, order_id: int, customer_id: int) -> Order:
        order = self.get_by_id(order_id, customer_id)

        if OrderStatus.CANCELLED not in VALID_TRANSITIONS[order.status]:
            raise ValueError(
                f"Order with status '{order.status}' cannot be cancelled."
            )

        self.stock_service.release_for_order(order)
        order.status = OrderStatus.CANCELLED
        return self.repo.update(order)

    def update_status(self, order_id: int, new_status: OrderStatus) -> Order:
        order = self.repo.get_by_id(order_id)

        if not order:
            raise ValueError("Order not found.")

        if new_status not in VALID_TRANSITIONS[order.status]:
            raise ValueError(
                f"Invalid transition: '{order.status}' → '{new_status}'."
            )

        order.status = new_status
        return self.repo.update(order)
