import datetime
from unittest.mock import patch

import jwt
import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "test-secret"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600
    app.config["AUTH_COOKIE_NAME"] = "access_token"
    app.config["AUTH_COOKIE_SECURE"] = False
    app.config["AUTH_COOKIE_SAMESITE"] = "Lax"
    with app.test_client() as client:
        yield client


def _token(role="regular", user_id="user-1", username="user1"):
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "app_metadata": {"role": role},
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def test_login_missing_credentials_returns_400(client):
    response = client.post("/api/v1/auth/login", json={"username": "", "password": ""})
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "invalid_request"


def test_login_invalid_credentials_returns_401(client):
    with patch("app.routes.api.auth_service.authenticate_user", return_value=None):
        response = client.post("/api/v1/auth/login", json={"username": "u1", "password": "badpass"})
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "invalid_credentials"


def test_login_configuration_error_returns_500(client):
    with patch("app.routes.api.auth_service.authenticate_user", side_effect=RuntimeError("config missing")):
        response = client.post("/api/v1/auth/login", json={"username": "u1", "password": "pass"})
    assert response.status_code == 500
    data = response.get_json()
    assert data["error"] == "server_configuration"


def test_login_success_for_admin_sets_cookie_and_redirect(client):
    user = {"id": "admin-1", "username": "admin_user", "role": "admin"}
    with patch("app.routes.api.auth_service.authenticate_user", return_value=user):
        with patch("app.routes.api.auth_service.create_access_token", return_value="signed-token"):
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "admin_user", "password": "Password123"},
            )

    assert response.status_code == 200
    data = response.get_json()
    assert data["redirect_to"] == "/admin"
    assert data["role"] == "admin"
    set_cookie = response.headers.get("Set-Cookie", "")
    assert "access_token=signed-token" in set_cookie


def test_login_success_for_regular_user_redirects_dashboard(client):
    user = {"id": "u-1", "username": "regular_user", "role": "regular"}
    with patch("app.routes.api.auth_service.authenticate_user", return_value=user):
        with patch("app.routes.api.auth_service.create_access_token", return_value="signed-token"):
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "regular_user", "password": "Password123"},
            )

    assert response.status_code == 200
    data = response.get_json()
    assert data["redirect_to"] == "/dashboard"
    assert data["role"] == "regular"


def test_auth_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "unauthorized"


def test_auth_me_with_invalid_token_returns_401(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "unauthorized"


def test_auth_me_returns_current_user_payload(client):
    token = _token(role="admin", user_id="admin-1", username="admin_user")
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["user"]["username"] == "admin_user"
    assert data["user"]["role"] == "admin"
