from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product


class VectorRepository:

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_similar_products(
        self, embedding: list[float], candidates: int
    ) -> list[tuple[Product, float]]:
        embedding_literal = "[" + ",".join(str(value) for value in embedding) + "]"
        statement = text(
            """
            SELECT products.*,
                   1 - (products.embedding <=> CAST(:embedding AS vector))
                       AS similarity_score
            FROM products
            WHERE is_active = true
              AND stock > 0
              AND embedding IS NOT NULL
            ORDER BY products.embedding <=> CAST(:embedding AS vector)
            LIMIT :candidates
            """
        )
        rows = self.db.execute(
            statement,
            {"embedding": embedding_literal, "candidates": candidates},
        ).all()

        if not rows:
            return []

        product_ids = [row.id for row in rows]
        products_by_id = {
            product.id: product
            for product in (
                self.db.query(Product)
                .options(joinedload(Product.category))
                .filter(Product.id.in_(product_ids))
                .all()
            )
        }

        return [
            (products_by_id[row.id], float(row.similarity_score))
            for row in rows
            if row.id in products_by_id
        ]

    def get_products_by_category(self, category_id: int) -> list[Product]:
        return (
            self.db.query(Product)
            .options(joinedload(Product.category))
            .filter(
                Product.category_id == category_id,
                Product.is_active == True,
            )
            .all()
        )

    def get_category_product_count(self, category_id: int) -> int:
        return (
            self.db.query(Product)
            .filter(
                Product.category_id == category_id,
                Product.is_active == True,
            )
            .count()
        )

    def get_all_active_products(self) -> list[Product]:
        return (
            self.db.query(Product)
            .options(joinedload(Product.category))
            .filter(Product.is_active == True)
            .all()
        )

    def count_active_without_indexed_at(self) -> int:
        return (
            self.db.query(Product)
            .filter(
                Product.is_active == True,
                Product.indexed_at.is_(None),
            )
            .count()
        )
