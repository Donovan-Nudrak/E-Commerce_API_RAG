from sqlalchemy.orm import Session

from app.models.cart import Cart
from app.models.cart_item import CartItem


class CartRepository:

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_customer_id(self, customer_id: int) -> Cart | None:
        return self.db.query(Cart).filter(Cart.customer_id == customer_id).first()

    def create(self, customer_id: int) -> Cart:
        cart = Cart(customer_id=customer_id)
        self.db.add(cart)
        self.db.commit()
        self.db.refresh(cart)
        return cart

    def get_item(self, cart_id: int, product_id: int) -> CartItem | None:
        return (
            self.db.query(CartItem)
            .filter(
                CartItem.cart_id == cart_id,
                CartItem.product_id == product_id,
            )
            .first()
        )

    def get_item_by_id(self, item_id: int) -> CartItem | None:
        return self.db.query(CartItem).filter(CartItem.id == item_id).first()

    def add_item(self, cart_id: int, product_id: int, quantity: int) -> CartItem:
        item = CartItem(cart_id=cart_id, product_id=product_id, quantity=quantity)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_item(self, item: CartItem, quantity: int) -> CartItem:
        item.quantity = quantity
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_item(self, item: CartItem) -> None:
        self.db.delete(item)
        self.db.commit()

    def clear(self, cart: Cart) -> None:
        self.db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        self.db.commit()
