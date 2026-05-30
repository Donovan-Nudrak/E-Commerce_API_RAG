from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.product import ProductResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=list[ProductResponse])
def get_all(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    category_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> list[ProductResponse]:
    return ProductService(db).get_all(
        skip=skip, limit=limit, category_id=category_id
    )


@router.get("/search", response_model=list[ProductResponse])
def search(
    q: str = Query(min_length=1),
    db: Session = Depends(get_db),
) -> list[ProductResponse]:
    return ProductService(db).search(q)


@router.get("/featured", response_model=list[ProductResponse])
def get_featured(db: Session = Depends(get_db)) -> list[ProductResponse]:
    return ProductService(db).get_featured()


@router.get("/offers", response_model=list[ProductResponse])
def get_offers(db: Session = Depends(get_db)) -> list[ProductResponse]:
    return ProductService(db).get_offers()


@router.get("/{product_id}", response_model=ProductResponse)
def get_by_id(product_id: int, db: Session = Depends(get_db)) -> ProductResponse:
    try:
        return ProductService(db).get_by_id(product_id, active_only=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
