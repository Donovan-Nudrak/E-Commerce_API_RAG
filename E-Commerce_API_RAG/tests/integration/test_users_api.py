import pytest

pytestmark = pytest.mark.integration


def test_get_profile(client, customer_auth):
    response = client.get("/api/v1/users/profile", headers=customer_auth)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "customer_test@example.com"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "Customer"
    assert data["role"] == "Customer"
    assert "phone" in data


def test_update_profile(client, customer_auth):
    response = client.put(
        "/api/v1/users/profile",
        headers=customer_auth,
        json={
            "first_name": "Updated",
            "last_name": "User",
            "phone": "+1234567890",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "User"
    assert data["phone"] == "+1234567890"


def test_delete_profile_and_unauthorized_after(client):
    email = "delete_me@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Delete",
            "last_name": "Me",
            "email": email,
            "password": "password123",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    delete = client.delete("/api/v1/users/profile", headers=headers)
    assert delete.status_code == 204

    after = client.get("/api/v1/users/profile", headers=headers)
    assert after.status_code == 401
