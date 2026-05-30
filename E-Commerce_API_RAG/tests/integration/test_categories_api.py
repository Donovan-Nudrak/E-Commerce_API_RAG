import pytest

pytestmark = pytest.mark.integration


def test_list_categories_public(client):
    response = client.get("/api/v1/categories/")
    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["name"] == "Electronics"


def test_get_category_by_id(client, db_session):
    from app.models.category import Category

    category = db_session.query(Category).first()
    response = client.get(f"/api/v1/categories/{category.id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Electronics"


def test_admin_category_crud(client, admin_auth):
    create = client.post(
        "/api/v1/admin/categories",
        headers=admin_auth,
        json={"name": "Books"},
    )
    assert create.status_code == 201
    category_id = create.json()["id"]
    assert create.json()["name"] == "Books"

    update = client.put(
        f"/api/v1/admin/categories/{category_id}",
        headers=admin_auth,
        json={"name": "Books & Media"},
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Books & Media"

    delete = client.delete(
        f"/api/v1/admin/categories/{category_id}",
        headers=admin_auth,
    )
    assert delete.status_code == 204


def test_create_category_requires_admin(client, customer_auth):
    response = client.post(
        "/api/v1/admin/categories",
        headers=customer_auth,
        json={"name": "Unauthorized"},
    )
    assert response.status_code == 403
