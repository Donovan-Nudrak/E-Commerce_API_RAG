from sqlalchemy.orm import Session

from app.models.order import Order
from app.repositories.product_repository import ProductRepository


class StockService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.product_repo = ProductRepository(db)

    def reserve_for_cart_items(self, cart_items) -> None:
        """Reserve stock when creating an order from cart items."""
        for item in cart_items:
            product = item.product
            if product.stock < item.quantity:
                raise ValueError(
                    f"Insufficient stock for '{product.name}'. "
                    f"Available: {product.stock}"
                )
            product.stock -= item.quantity

    def release_for_order(self, order: Order) -> None:
        """Restore stock when a pending order is cancelled."""
        for item in order.items:
            product = self.product_repo.get_by_id(item.product_id)
            if product:
                product.stock += item.quantity
                self.product_repo.update(product)

    def confirm_for_order(self, order: Order) -> None:
        """Confirm reservation after payment. Stock was already decremented on order create."""
        return None
