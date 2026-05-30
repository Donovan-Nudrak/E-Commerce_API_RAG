import pytest

pytestmark = pytest.mark.integration


def test_cart_crud(client, customer_auth, product_id):
    empty = client.get("/api/v1/cart/", headers=customer_auth)
    assert empty.status_code == 200
    assert empty.json()["items"] == []

    added = client.post(
        "/api/v1/cart/items",
        headers=customer_auth,
        json={"product_id": product_id, "quantity": 2},
    )
    assert added.status_code == 201
    cart = added.json()
    assert len(cart["items"]) == 1
    item_id = cart["items"][0]["id"]
    assert cart["items"][0]["quantity"] == 2

    updated = client.put(
        f"/api/v1/cart/items/{item_id}",
        headers=customer_auth,
        json={"quantity": 3},
    )
    assert updated.status_code == 200
    assert updated.json()["items"][0]["quantity"] == 3

    removed = client.delete(
        f"/api/v1/cart/items/{item_id}",
        headers=customer_auth,
    )
    assert removed.status_code == 200
    assert removed.json()["items"] == []

    client.post(
        "/api/v1/cart/items",
        headers=customer_auth,
        json={"product_id": product_id, "quantity": 1},
    )
    cleared = client.delete("/api/v1/cart/clear", headers=customer_auth)
    assert cleared.status_code == 204

    final = client.get("/api/v1/cart/", headers=customer_auth)
    assert final.json()["items"] == []
