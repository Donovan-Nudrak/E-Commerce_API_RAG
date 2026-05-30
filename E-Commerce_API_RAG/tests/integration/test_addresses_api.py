import pytest

pytestmark = pytest.mark.integration


def test_address_crud(client, customer_auth):
    create = client.post(
        "/api/v1/addresses/",
        headers=customer_auth,
        json={
            "street": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
            "country": "USA",
        },
    )
    assert create.status_code == 201
    address = create.json()
    assert address["street"] == "123 Main St"

    listing = client.get("/api/v1/addresses/", headers=customer_auth)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    detail = client.get(
        f"/api/v1/addresses/{address['id']}",
        headers=customer_auth,
    )
    assert detail.status_code == 200

    updated = client.put(
        f"/api/v1/addresses/{address['id']}",
        headers=customer_auth,
        json={"city": "Chicago"},
    )
    assert updated.status_code == 200
    assert updated.json()["city"] == "Chicago"

    deleted = client.delete(
        f"/api/v1/addresses/{address['id']}",
        headers=customer_auth,
    )
    assert deleted.status_code == 204

    empty = client.get("/api/v1/addresses/", headers=customer_auth)
    assert empty.json() == []


def test_address_requires_auth(client):
    response = client.get("/api/v1/addresses/")
    assert response.status_code == 401


def test_address_not_found(client, customer_auth):
    response = client.get("/api/v1/addresses/9999", headers=customer_auth)
    assert response.status_code == 404


def test_payment_types_list(client):
    response = client.get("/api/v1/payment-types/")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert "Card" in names
    assert "Bank Transfer" in names

    domain_only = client.get("/api/v1/payment-types/?domain_only=true")
    domain_names = {item["name"] for item in domain_only.json()}
    assert domain_names == {"Card", "Bank Transfer", "Cash"}
