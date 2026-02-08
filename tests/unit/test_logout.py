import datetime

import jwt
import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "test-secret"
    app.config["AUTH_COOKIE_NAME"] = "access_token"
    app.config["AUTH_COOKIE_SECURE"] = False
    app.config["AUTH_COOKIE_SAMESITE"] = "Lax"
    with app.test_client() as client:
        yield client


def _token(user_id="admin-1", username="admin", role="admin"):
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "app_metadata": {"role": role},
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def test_logout_success_clears_session_and_cookies(client):
    with client.session_transaction() as sess:
        sess["user_id"] = "admin-1"
        sess["csrf_token"] = "token"

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "logged out" in data["message"].lower()

    with client.session_transaction() as sess:
        assert "user_id" not in sess
        assert "csrf_token" not in sess

    set_cookie_headers = "\n".join(response.headers.getlist("Set-Cookie"))
    assert "access_token=;" in set_cookie_headers
    assert "Max-Age=0" in set_cookie_headers or "expires=" in set_cookie_headers.lower()


def test_logout_requires_authentication(client):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 401
    data = response.get_json()
    assert data is not None
    assert data["error"] == "unauthorized"


def test_logout_with_invalid_token_returns_401(client):
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
    data = response.get_json()
    assert data is not None
    assert data["error"] == "unauthorized"
