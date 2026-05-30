import pytest

pytestmark = pytest.mark.integration


def test_public_product_catalog(client, product_id):
    listing = client.get("/api/v1/products/")
    assert listing.status_code == 200
    assert len(listing.json()) >= 1

    search = client.get("/api/v1/products/search", params={"q": "Test"})
    assert search.status_code == 200
    assert any(p["name"] == "Test Product" for p in search.json())

    featured = client.get("/api/v1/products/featured")
    assert featured.status_code == 200
    assert len(featured.json()) >= 1

    offers = client.get("/api/v1/products/offers")
    assert offers.status_code == 200
    assert len(offers.json()) >= 1

    detail = client.get(f"/api/v1/products/{product_id}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Test Product"


def test_admin_product_crud_and_soft_delete(client, admin_auth, db_session):
    from app.models.category import Category

    category_id = db_session.query(Category).first().id

    create = client.post(
        "/api/v1/admin/products",
        headers=admin_auth,
        json={
            "category_id": category_id,
            "name": "Admin Product",
            "description": "Created in test",
            "price": "50.00",
            "stock": 10,
        },
    )
    assert create.status_code == 201
    product_id = create.json()["id"]

    update = client.put(
        f"/api/v1/admin/products/{product_id}",
        headers=admin_auth,
        json={"name": "Admin Product Updated", "stock": 5},
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Admin Product Updated"
    assert update.json()["stock"] == 5

    delete = client.delete(
        f"/api/v1/admin/products/{product_id}",
        headers=admin_auth,
    )
    assert delete.status_code == 204

    public_detail = client.get(f"/api/v1/products/{product_id}")
    assert public_detail.status_code == 404
