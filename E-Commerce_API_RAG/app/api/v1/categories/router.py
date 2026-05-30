from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.category import CategoryResponse
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/", response_model=list[CategoryResponse])
def get_all(db: Session = Depends(get_db)) -> list[CategoryResponse]:
    return CategoryService(db).get_all()


@router.get("/{category_id}", response_model=CategoryResponse)
def get_by_id(category_id: int, db: Session = Depends(get_db)) -> CategoryResponse:
    try:
        return CategoryService(db).get_by_id(category_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
