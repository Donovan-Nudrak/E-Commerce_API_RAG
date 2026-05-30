import pytest

pytestmark = pytest.mark.integration


def _create_order(client, customer_auth, product_id):
    client.post(
        "/api/v1/cart/items",
        headers=customer_auth,
        json={"product_id": product_id, "quantity": 2},
    )
    response = client.post("/api/v1/orders/", headers=customer_auth)
    assert response.status_code == 201
    return response.json()


def test_order_full_lifecycle(client, customer_auth, admin_auth, product_id):
    order = _create_order(client, customer_auth, product_id)
    assert order["status"] == "PENDING"

    pay = client.put(
        f"/api/v1/admin/orders/{order['id']}/status",
        headers=admin_auth,
        json={"status": "PAID"},
    )
    assert pay.status_code == 200
    assert pay.json()["status"] == "PAID"

    detail = client.get(f"/api/v1/orders/{order['id']}", headers=customer_auth)
    assert detail.json()["status"] == "PAID"

    ship = client.put(
        f"/api/v1/admin/orders/{order['id']}/status",
        headers=admin_auth,
        json={"status": "SHIPPED"},
    )
    assert ship.status_code == 200
    assert ship.json()["status"] == "SHIPPED"

    deliver = client.put(
        f"/api/v1/admin/orders/{order['id']}/status",
        headers=admin_auth,
        json={"status": "DELIVERED"},
    )
    assert deliver.status_code == 200
    assert deliver.json()["status"] == "DELIVERED"


def test_create_order_empty_cart(client, customer_auth):
    response = client.post("/api/v1/orders/", headers=customer_auth)
    assert response.status_code == 400


def test_cancel_pending_order(client, customer_auth, product_id):
    order = _create_order(client, customer_auth, product_id)

    response = client.put(
        f"/api/v1/orders/{order['id']}/cancel",
        headers=customer_auth,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_invalid_status_transition(client, customer_auth, admin_auth, product_id):
    order = _create_order(client, customer_auth, product_id)

    response = client.put(
        f"/api/v1/admin/orders/{order['id']}/status",
        headers=admin_auth,
        json={"status": "SHIPPED"},
    )
    assert response.status_code == 400


def test_admin_list_orders(client, customer_auth, admin_auth, product_id):
    _create_order(client, customer_auth, product_id)

    response = client.get("/api/v1/admin/orders", headers=admin_auth)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_stock_decremented_after_order(client, customer_auth, product_id, db_session):
    from app.models.product import Product

    product = db_session.query(Product).filter(Product.id == product_id).first()
    initial_stock = product.stock

    _create_order(client, customer_auth, product_id)

    db_session.refresh(product)
    assert product.stock == initial_stock - 2


def test_stock_restored_after_cancel(client, customer_auth, product_id, db_session):
    from app.models.product import Product

    product = db_session.query(Product).filter(Product.id == product_id).first()
    initial_stock = product.stock

    order = _create_order(client, customer_auth, product_id)

    client.put(
        f"/api/v1/orders/{order['id']}/cancel",
        headers=customer_auth,
    )

    db_session.refresh(product)
    assert product.stock == initial_stock
