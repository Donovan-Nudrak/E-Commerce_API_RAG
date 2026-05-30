import pytest

pytestmark = pytest.mark.integration


def test_payment_methods_crud(client, customer_auth, payment_type_ids):
    create = client.post(
        "/api/v1/payments/methods",
        headers=customer_auth,
        json={"payment_type_id": payment_type_ids["card"], "reference": "****4242"},
    )
    assert create.status_code == 201
    method_id = create.json()["id"]

    listing = client.get("/api/v1/payments/methods", headers=customer_auth)
    assert listing.status_code == 200
    assert len(listing.json()) >= 1

    delete = client.delete(
        f"/api/v1/payments/methods/{method_id}", headers=customer_auth
    )
    assert delete.status_code == 204


def test_delete_unknown_payment_method(client, customer_auth):
    response = client.delete(
        "/api/v1/payments/methods/9999",
        headers=customer_auth,
    )
    assert response.status_code == 404
