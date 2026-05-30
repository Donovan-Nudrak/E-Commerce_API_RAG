from sqlalchemy.orm import Session

from app.models.cart import Cart
from app.repositories.cart_repository import CartRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.cart import CartItemAdd, CartItemUpdate


class CartService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CartRepository(db)
        self.product_repo = ProductRepository(db)

    def _get_or_create_cart(self, customer_id: int) -> Cart:
        cart = self.repo.get_by_customer_id(customer_id)
        if not cart:
            cart = self.repo.create(customer_id)
        return cart

    def get_cart(self, customer_id: int) -> Cart:
        return self._get_or_create_cart(customer_id)

    def add_item(self, customer_id: int, data: CartItemAdd) -> Cart:
        product = self.product_repo.get_by_id(data.product_id)

        if not product or not product.is_active:
            raise ValueError("Product not found or inactive.")

        if product.stock < data.quantity:
            raise ValueError(f"Insufficient stock. Available: {product.stock}")

        cart = self._get_or_create_cart(customer_id)
        existing_item = self.repo.get_item(cart.id, data.product_id)

        if existing_item:
            new_quantity = existing_item.quantity + data.quantity
            if product.stock < new_quantity:
                raise ValueError(f"Insufficient stock. Available: {product.stock}")
            self.repo.update_item(existing_item, new_quantity)
        else:
            self.repo.add_item(cart.id, data.product_id, data.quantity)

        return self.repo.get_by_customer_id(customer_id)

    def update_item(
        self, customer_id: int, item_id: int, data: CartItemUpdate
    ) -> Cart:
        cart = self._get_or_create_cart(customer_id)
        item = self.repo.get_item_by_id(item_id)

        if not item or item.cart_id != cart.id:
            raise ValueError("Item not found in cart.")

        if item.product.stock < data.quantity:
            raise ValueError(f"Insufficient stock. Available: {item.product.stock}")

        self.repo.update_item(item, data.quantity)
        return self.repo.get_by_customer_id(customer_id)

    def delete_item(self, customer_id: int, item_id: int) -> Cart:
        cart = self._get_or_create_cart(customer_id)
        item = self.repo.get_item_by_id(item_id)

        if not item or item.cart_id != cart.id:
            raise ValueError("Item not found in cart.")

        self.repo.delete_item(item)
        return self.repo.get_by_customer_id(customer_id)

    def clear(self, customer_id: int) -> None:
        cart = self._get_or_create_cart(customer_id)
        self.repo.clear(cart)
