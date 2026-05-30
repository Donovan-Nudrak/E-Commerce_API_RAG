import pytest
from unittest.mock import AsyncMock, patch


pytestmark = pytest.mark.integration


def test_register_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
            "password": "securepass123",
        },
    )
    assert response.status_code == 201
    assert "customer_id" in response.json()


def test_register_duplicate_email(client, customer_auth):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Dup",
            "last_name": "User",
            "email": "customer_test@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 400


def test_login_success(client, customer_auth):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "customer_test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_invalid_credentials(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "customer_test@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_me_authenticated(client, customer_auth):
    response = client.get("/api/v1/auth/me", headers=customer_auth)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "customer_test@example.com"
    assert data["role"] == "Customer"
    assert "phone" in data


def test_me_unauthorized(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_refresh_token(client, customer_auth):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "customer_test@example.com", "password": "password123"},
    )
    refresh_token = login.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh-token",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_logout(client, customer_auth):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "customer_test@example.com", "password": "password123"},
    )
    refresh_token = login.json()["refresh_token"]
    headers = customer_auth

    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200

    refresh_response = client.post(
        "/api/v1/auth/refresh-token",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401


@patch("app.services.auth_service.send_reset_password_email", new_callable=AsyncMock)
def test_forgot_password(mock_send, client, customer_auth):
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "customer_test@example.com"},
    )
    assert response.status_code == 200
    mock_send.assert_called_once()


def test_register_rate_limit(client):
    for i in range(5):
        client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Rate",
                "last_name": f"User{i}",
                "email": f"rate{i}@example.com",
                "password": "password123",
            },
        )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Rate",
            "last_name": "Blocked",
            "email": "rate_blocked@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 429
