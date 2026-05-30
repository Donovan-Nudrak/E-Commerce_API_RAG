from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.v1.auth.dependencies import get_current_customer, require_admin
from app.database.session import get_db
from app.models.customer import Customer
from app.models.order import OrderStatus
from app.schemas.admin import (
    AdminOrderResponse,
    CustomerAdminDetailResponse,
    CustomerAdminResponse,
    CustomerAdminUpdate,
    DashboardResponse,
)
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.order import OrderStatusUpdate
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.admin_service import AdminService
from app.services.category_service import CategoryService

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    return AdminService(db).get_dashboard()


@router.get("/orders", response_model=list[AdminOrderResponse])
def list_orders(
    status: OrderStatus | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[AdminOrderResponse]:
    return AdminService(db).list_orders(skip=skip, limit=limit, status=status)


@router.get("/orders/{order_id}", response_model=AdminOrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)) -> AdminOrderResponse:
    try:
        return AdminService(db).get_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/orders/{order_id}/status", response_model=AdminOrderResponse)
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
) -> AdminOrderResponse:
    try:
        return AdminService(db).update_order_status(order_id, data.status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/customers", response_model=list[CustomerAdminResponse])
def list_customers(
    search: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[CustomerAdminResponse]:
    return AdminService(db).list_customers(skip=skip, limit=limit, search=search)


@router.get("/customers/{customer_id}", response_model=CustomerAdminDetailResponse)
def get_customer(
    customer_id: int, db: Session = Depends(get_db)
) -> CustomerAdminDetailResponse:
    try:
        return AdminService(db).get_customer(customer_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/customers/{customer_id}", response_model=CustomerAdminDetailResponse)
def update_customer(
    customer_id: int,
    data: CustomerAdminUpdate,
    admin: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
) -> CustomerAdminDetailResponse:
    try:
        return AdminService(db).update_customer(customer_id, data, admin.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryResponse]:
    return CategoryService(db).get_all()


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    data: CategoryCreate, db: Session = Depends(get_db)
) -> CategoryResponse:
    try:
        return CategoryService(db).create(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
) -> CategoryResponse:
    try:
        return CategoryService(db).update(category_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> None:
    try:
        CategoryService(db).delete(category_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/products", response_model=list[ProductResponse])
def list_products(
    is_active: bool | None = None,
    low_stock: bool = False,
    search: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[ProductResponse]:
    return AdminService(db).list_products(
        skip=skip,
        limit=limit,
        is_active=is_active,
        low_stock=low_stock,
        search=search,
    )


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductResponse:
    try:
        return AdminService(db).get_product(product_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED
)
def create_product(
    data: ProductCreate, db: Session = Depends(get_db)
) -> ProductResponse:
    return AdminService(db).create_product(data)


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int, data: ProductUpdate, db: Session = Depends(get_db)
) -> ProductResponse:
    try:
        return AdminService(db).update_product(product_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> None:
    try:
        AdminService(db).delete_product(product_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/products/{product_id}/image", response_model=ProductResponse)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ProductResponse:
    try:
        return await AdminService(db).upload_product_image(product_id, file)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
