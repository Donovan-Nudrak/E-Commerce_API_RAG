import logging

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductUpdate
from app.utils.storage import upload_image

logger = logging.getLogger(__name__)


class ProductService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ProductRepository(db)

    def get_all(
        self,
        skip: int = 0,
        limit: int = 20,
        category_id: int | None = None,
    ) -> list[Product]:
        return self.repo.get_all(skip=skip, limit=limit, category_id=category_id)

    def get_by_id(self, product_id: int, *, active_only: bool = False) -> Product:
        product = self.repo.get_by_id(product_id)
        if not product:
            raise ValueError("Product not found.")
        if active_only and not product.is_active:
            raise ValueError("Product not found.")
        return product

    def search(self, query: str) -> list[Product]:
        return self.repo.search(query)

    def get_offers(self) -> list[Product]:
        return self.repo.get_offers()

    def get_featured(self) -> list[Product]:
        return self.repo.get_featured()

    def create(self, data: ProductCreate) -> Product:
        product = Product(
            category_id=data.category_id,
            name=data.name,
            description=data.description,
            barcode=data.barcode,
            price=data.price,
            discount_price=data.discount_price,
            stock=data.stock,
        )
        return self.repo.create(product)

    def update(self, product_id: int, data: ProductUpdate) -> Product:
        product = self.get_by_id(product_id)

        for field, value in data.model_dump(exclude_none=True).items():
            setattr(product, field, value)

        updated = self.repo.update(product)
        self._try_reindex_product(updated)
        return updated

    def _try_reindex_product(self, product: Product) -> None:
        if not product.is_active:
            return
        try:
            from app.services.rag_service import RAGService

            RAGService(self.db).reindex_product(product.id)
        except ValueError:
            pass
        except Exception as exc:
            logger.warning("RAG reindex after product change failed: %s", exc)

    def delete(self, product_id: int) -> Product:
        product = self.get_by_id(product_id)
        return self.repo.soft_delete(product)

    async def upload_product_image(
        self, product_id: int, file: UploadFile
    ) -> Product:
        product = self.get_by_id(product_id)
        image_url = await upload_image(file)

        if not image_url:
            raise ValueError("Failed to upload image.")

        product.image_url = image_url
        updated = self.repo.update(product)
        self._try_reindex_product(updated)
        return updated
