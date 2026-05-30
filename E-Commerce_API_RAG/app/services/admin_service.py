from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.admin import (
    AdminOrderResponse,
    CustomerAdminDetailResponse,
    CustomerAdminResponse,
    CustomerAdminUpdate,
    DashboardRecentOrder,
    DashboardResponse,
)
from app.schemas.product import ProductCreate, ProductUpdate
from app.core.constants import LOW_STOCK_THRESHOLD
from app.services.order_service import OrderService
from app.services.product_service import ProductService


class AdminService:

    def __init__(self, db: Session) -> None:
        self.db = db
        self.order_repo = OrderRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.product_repo = ProductRepository(db)
        self.role_repo = RoleRepository(db)
        self.order_service = OrderService(db)
        self.product_service = ProductService(db)

    @staticmethod
    def _order_to_admin_response(order: Order) -> AdminOrderResponse:
        return AdminOrderResponse(
            id=order.id,
            customer_id=order.customer_id,
            customer_email=order.customer.email,
            customer_first_name=order.customer.first_name,
            customer_last_name=order.customer.last_name,
            payment_method_id=order.payment_method_id,
            total=order.total,
            status=order.status,
            items=order.items,
            created_at=order.created_at,
        )

    def get_dashboard(self) -> DashboardResponse:
        active, inactive = self.product_repo.count_by_active()
        orders_by_status = self.order_repo.count_by_status()

        for status in OrderStatus:
            orders_by_status.setdefault(status.value, 0)

        recent = [
            DashboardRecentOrder(
                id=order.id,
                customer_email=order.customer.email,
                customer_first_name=order.customer.first_name,
                customer_last_name=order.customer.last_name,
                total=order.total,
                status=order.status,
                created_at=order.created_at,
            )
            for order in self.order_repo.get_recent(limit=10)
        ]

        return DashboardResponse(
            total_customers=self.customer_repo.count_all(),
            total_products_active=active,
            total_products_inactive=inactive,
            low_stock_products=self.product_repo.count_low_stock(LOW_STOCK_THRESHOLD),
            total_orders=self.order_repo.count_all(),
            orders_by_status=orders_by_status,
            total_revenue=self.order_repo.sum_revenue(),
            recent_orders=recent,
        )

    def list_orders(
        self,
        skip: int = 0,
        limit: int = 20,
        status: OrderStatus | None = None,
    ) -> list[AdminOrderResponse]:
        orders = self.order_repo.get_all_admin(skip=skip, limit=limit, status=status)
        return [self._order_to_admin_response(order) for order in orders]

    def get_order(self, order_id: int) -> AdminOrderResponse:
        order = self.order_repo.get_by_id_admin(order_id)
        if not order:
            raise ValueError("Order not found.")
        return self._order_to_admin_response(order)

    def update_order_status(self, order_id: int, new_status: OrderStatus) -> AdminOrderResponse:
        order = self.order_service.update_status(order_id, new_status)
        order = self.order_repo.get_by_id_admin(order.id)
        return self._order_to_admin_response(order)

    def list_customers(
        self,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> list[CustomerAdminResponse]:
        customers = self.customer_repo.get_all_admin(
            skip=skip, limit=limit, search=search
        )
        return [
            CustomerAdminResponse(
                id=c.id,
                role_id=c.role_id,
                role_name=c.role.name,
                first_name=c.first_name,
                last_name=c.last_name,
                email=c.email,
                phone=c.phone,
                created_at=c.created_at,
            )
            for c in customers
        ]

    def get_customer(self, customer_id: int) -> CustomerAdminDetailResponse:
        customer = self.customer_repo.get_by_id_with_role(customer_id)
        if not customer:
            raise ValueError("Customer not found.")

        orders_count, total_spent = self.customer_repo.get_orders_stats(customer_id)

        return CustomerAdminDetailResponse(
            id=customer.id,
            role_id=customer.role_id,
            role_name=customer.role.name,
            first_name=customer.first_name,
            last_name=customer.last_name,
            email=customer.email,
            phone=customer.phone,
            created_at=customer.created_at,
            orders_count=orders_count,
            total_spent=total_spent,
        )

    def update_customer(
        self, customer_id: int, data: CustomerAdminUpdate, acting_admin_id: int
    ) -> CustomerAdminDetailResponse:
        customer = self.customer_repo.get_by_id_with_role(customer_id)
        if not customer:
            raise ValueError("Customer not found.")

        updates = data.model_dump(exclude_none=True)

        if "role_id" in updates:
            new_role = self.role_repo.get_by_id(updates["role_id"])
            if not new_role:
                raise ValueError("Role not found.")

            is_current_admin = customer.role.name == "Administrator"
            is_demoting = new_role.name != "Administrator"

            if is_current_admin and is_demoting:
                if self.customer_repo.count_admins() <= 1:
                    raise ValueError("Cannot demote the only administrator.")

        for field, value in updates.items():
            setattr(customer, field, value)

        self.customer_repo.update(customer)
        return self.get_customer(customer_id)

    def list_products(
        self,
        skip: int = 0,
        limit: int = 20,
        is_active: bool | None = None,
        low_stock: bool = False,
        search: str | None = None,
    ):
        return self.product_repo.get_all_admin(
            skip=skip,
            limit=limit,
            is_active=is_active,
            low_stock=low_stock,
            search=search,
        )

    def get_product(self, product_id: int):
        return self.product_service.get_by_id(product_id)

    def create_product(self, data: ProductCreate):
        return self.product_service.create(data)

    def update_product(self, product_id: int, data: ProductUpdate):
        return self.product_service.update(product_id, data)

    def delete_product(self, product_id: int):
        return self.product_service.delete(product_id)

    async def upload_product_image(self, product_id: int, file: UploadFile):
        return await self.product_service.upload_product_image(product_id, file)
