from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

from app.models.order import OrderStatus
from app.schemas.admin import CustomerAdminUpdate
from app.schemas.product import ProductUpdate
from app.services.admin_service import AdminService


def _make_order(
    order_id: int = 1,
    status: OrderStatus = OrderStatus.PENDING,
) -> MagicMock:
    order = MagicMock()
    order.id = order_id
    order.customer_id = 10
    order.payment_method_id = None
    order.total = Decimal("99.99")
    order.status = status
    order.created_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
    order.items = []

    customer = MagicMock()
    customer.email = "user@test.com"
    customer.first_name = "John"
    customer.last_name = "Doe"
    order.customer = customer

    return order


def _make_customer(customer_id: int = 10, role_name: str = "Customer") -> MagicMock:
    customer = MagicMock()
    customer.id = customer_id
    customer.role_id = 1 if role_name == "Customer" else 2
    customer.first_name = "John"
    customer.last_name = "Doe"
    customer.email = "user@test.com"
    customer.phone = None
    customer.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    role = MagicMock()
    role.name = role_name
    customer.role = role

    return customer


@pytest.fixture
def service() -> AdminService:
    db = MagicMock()
    svc = AdminService(db)
    svc.order_repo = MagicMock()
    svc.customer_repo = MagicMock()
    svc.product_repo = MagicMock()
    svc.order_service = MagicMock()
    svc.product_service = MagicMock()
    return svc


def test_get_dashboard(service: AdminService) -> None:
    service.customer_repo.count_all.return_value = 50
    service.product_repo.count_by_active.return_value = (40, 5)
    service.product_repo.count_low_stock.return_value = 3
    service.order_repo.count_all.return_value = 120
    service.order_repo.count_by_status.return_value = {
        "PENDING": 10,
        "PAID": 30,
    }
    service.order_repo.sum_revenue.return_value = Decimal("15000.00")
    service.order_repo.get_recent.return_value = [_make_order()]

    dashboard = service.get_dashboard()

    assert dashboard.total_customers == 50
    assert dashboard.total_products_active == 40
    assert dashboard.total_products_inactive == 5
    assert dashboard.low_stock_products == 3
    assert dashboard.total_orders == 120
    assert dashboard.orders_by_status["PENDING"] == 10
    assert dashboard.orders_by_status["PAID"] == 30
    assert dashboard.orders_by_status["SHIPPED"] == 0
    assert dashboard.total_revenue == Decimal("15000.00")
    assert len(dashboard.recent_orders) == 1


def test_list_orders_with_status_filter(service: AdminService) -> None:
    order = _make_order(status=OrderStatus.PAID)
    service.order_repo.get_all_admin.return_value = [order]

    result = service.list_orders(status=OrderStatus.PAID)

    service.order_repo.get_all_admin.assert_called_once_with(
        skip=0, limit=20, status=OrderStatus.PAID
    )
    assert result[0].status == OrderStatus.PAID
    assert result[0].customer_email == "user@test.com"


def test_get_order_not_found(service: AdminService) -> None:
    service.order_repo.get_by_id_admin.return_value = None

    with pytest.raises(ValueError, match="Order not found"):
        service.get_order(999)


def test_update_order_status(service: AdminService) -> None:
    updated = _make_order(status=OrderStatus.SHIPPED)
    service.order_service.update_status.return_value = updated
    service.order_repo.get_by_id_admin.return_value = updated

    result = service.update_order_status(1, OrderStatus.SHIPPED)

    service.order_service.update_status.assert_called_once_with(1, OrderStatus.SHIPPED)
    assert result.status == OrderStatus.SHIPPED


def test_list_customers(service: AdminService) -> None:
    service.customer_repo.get_all_admin.return_value = [_make_customer()]

    result = service.list_customers(search="john")

    service.customer_repo.get_all_admin.assert_called_once_with(
        skip=0, limit=20, search="john"
    )
    assert result[0].role_name == "Customer"


def test_get_customer_detail(service: AdminService) -> None:
    service.customer_repo.get_by_id_with_role.return_value = _make_customer()
    service.customer_repo.get_orders_stats.return_value = (5, Decimal("500.00"))

    result = service.get_customer(10)

    assert result.orders_count == 5
    assert result.total_spent == Decimal("500.00")


def test_update_customer_demote_only_admin_blocked(service: AdminService) -> None:
    admin_customer = _make_customer(customer_id=1, role_name="Administrator")
    service.customer_repo.get_by_id_with_role.return_value = admin_customer
    service.customer_repo.count_admins.return_value = 1

    customer_role = MagicMock()
    customer_role.id = 1
    customer_role.name = "Customer"
    service.db.query.return_value.filter.return_value.first.return_value = customer_role

    data = CustomerAdminUpdate(role_id=1)

    with pytest.raises(ValueError, match="only administrator"):
        service.update_customer(1, data, acting_admin_id=1)


def test_update_customer_success(service: AdminService) -> None:
    customer = _make_customer()
    service.customer_repo.get_by_id_with_role.return_value = customer
    service.customer_repo.get_orders_stats.return_value = (2, Decimal("100.00"))

    data = CustomerAdminUpdate(phone="+1234567890")
    service.update_customer(10, data, acting_admin_id=2)

    assert customer.phone == "+1234567890"
    service.customer_repo.update.assert_called_once()


def test_list_products_admin(service: AdminService) -> None:
    product = MagicMock()
    product.is_active = False
    service.product_repo.get_all_admin.return_value = [product]

    result = service.list_products(is_active=False, low_stock=True, search="phone")

    service.product_repo.get_all_admin.assert_called_once_with(
        skip=0,
        limit=20,
        is_active=False,
        low_stock=True,
        search="phone",
    )
    assert len(result) == 1


def test_product_update_with_is_active(service: AdminService) -> None:
    product = MagicMock()
    product.is_active = False
    service.product_service.update.return_value = product

    data = ProductUpdate(is_active=True)
    result = service.update_product(1, data)

    service.product_service.update.assert_called_once_with(1, data)
    assert result == product


def test_product_reactivate_via_update_schema() -> None:
    data = ProductUpdate(is_active=True)
    assert data.is_active is True
