from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.constants import LOW_STOCK_THRESHOLD
from app.models.product import Product


class ProductRepository:

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        category_id: int | None = None,
    ) -> list[Product]:
        query = self.db.query(Product).filter(Product.is_active == True)
        if category_id is not None:
            query = query.filter(Product.category_id == category_id)
        return query.offset(skip).limit(limit).all()

    def get_by_id(self, product_id: int) -> Product | None:
        return self.db.query(Product).filter(Product.id == product_id).first()

    def search(self, query: str) -> list[Product]:
        return (
            self.db.query(Product)
            .filter(
                Product.is_active == True,
                Product.name.ilike(f"%{query}%"),
            )
            .all()
        )

    def get_offers(self) -> list[Product]:
        return (
            self.db.query(Product)
            .filter(
                Product.is_active == True,
                Product.discount_price != None,
            )
            .all()
        )

    def get_featured(self) -> list[Product]:
        return (
            self.db.query(Product)
            .filter(Product.is_active == True)
            .order_by(Product.created_at.desc())
            .limit(10)
            .all()
        )

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update(self, product: Product) -> Product:
        self.db.commit()
        self.db.refresh(product)
        return product

    def soft_delete(self, product: Product) -> Product:
        product.is_active = False
        self.db.commit()
        self.db.refresh(product)
        return product

    def get_all_admin(
        self,
        skip: int = 0,
        limit: int = 20,
        is_active: bool | None = None,
        low_stock: bool = False,
        search: str | None = None,
    ) -> list[Product]:
        query = self.db.query(Product).order_by(Product.created_at.desc())

        if is_active is not None:
            query = query.filter(Product.is_active == is_active)
        if low_stock:
            query = query.filter(
                Product.is_active == True,
                Product.stock < LOW_STOCK_THRESHOLD,
            )
        if search:
            query = query.filter(Product.name.ilike(f"%{search}%"))

        return query.offset(skip).limit(limit).all()

    def count_by_active(self) -> tuple[int, int]:
        active = (
            self.db.query(func.count(Product.id))
            .filter(Product.is_active == True)
            .scalar()
            or 0
        )
        inactive = (
            self.db.query(func.count(Product.id))
            .filter(Product.is_active == False)
            .scalar()
            or 0
        )
        return active, inactive

    def count_low_stock(self, threshold: int = LOW_STOCK_THRESHOLD) -> int:
        return (
            self.db.query(func.count(Product.id))
            .filter(Product.is_active == True, Product.stock < threshold)
            .scalar()
            or 0
        )
