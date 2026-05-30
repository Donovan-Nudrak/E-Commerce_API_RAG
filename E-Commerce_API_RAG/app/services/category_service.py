from sqlalchemy.orm import Session

from app.models.category import Category
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CategoryRepository(db)

    def get_all(self) -> list[Category]:
        return self.repo.get_all()

    def get_by_id(self, category_id: int) -> Category:
        category = self.repo.get_by_id(category_id)
        if not category:
            raise ValueError("Category not found.")
        return category

    def create(self, data: CategoryCreate) -> Category:
        existing = self.repo.get_by_name(data.name)
        if existing:
            raise ValueError("Category already exists.")
        return self.repo.create(Category(name=data.name))

    def update(self, category_id: int, data: CategoryUpdate) -> Category:
        category = self.get_by_id(category_id)
        category.name = data.name
        return self.repo.update(category)

    def delete(self, category_id: int) -> None:
        category = self.get_by_id(category_id)
        self.repo.delete(category)
