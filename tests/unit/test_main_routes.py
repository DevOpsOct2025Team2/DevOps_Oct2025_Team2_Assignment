import datetime

import jwt
import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "test-secret"
    app.config["AUTH_COOKIE_NAME"] = "access_token"
    with app.test_client() as client:
        yield client


def _token(role="regular", user_id="user-1", username="user1"):
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def test_index_route_returns_app_status(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "running"


def test_info_route_returns_metadata(client):
    response = client.get("/info")
    assert response.status_code == 200
    data = response.get_json()
    assert data["app"] == "Flask DevOps Demo"


def test_login_route_sanitizes_external_next_param(client):
    response = client.get("/login?next=https://evil.example")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'id="nextPath" value=""' in body
    assert "evil.example" not in body


def test_login_route_keeps_internal_next_param(client):
    response = client.get("/login?next=/dashboard")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'id="nextPath" value="/dashboard"' in body


def test_dashboard_requires_authentication(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login?next=/dashboard" in response.headers["Location"]


def test_dashboard_allows_regular_user(client):
    response = client.get(
        "/dashboard",
        headers={"Authorization": f"Bearer {_token(role='regular')}"},
    )
    assert response.status_code == 200
    assert "Dashboard" in response.get_data(as_text=True)


def test_dashboard_redirects_admin_to_admin_page(client):
    response = client.get(
        "/dashboard",
        headers={"Authorization": f"Bearer {_token(role='admin', user_id='admin-1', username='admin')}"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin")


def test_admin_requires_authentication(client):
    response = client.get("/admin")
    assert response.status_code == 302
    assert "/login?next=/admin" in response.headers["Location"]


def test_admin_allows_admin_user(client):
    response = client.get(
        "/admin",
        headers={"Authorization": f"Bearer {_token(role='admin', user_id='admin-1', username='admin')}"},
    )
    assert response.status_code == 200
    assert "Admin Dashboard" in response.get_data(as_text=True)


def test_admin_redirects_regular_user_to_dashboard(client):
    response = client.get(
        "/admin",
        headers={"Authorization": f"Bearer {_token(role='regular')}"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_main_logout_redirects_to_login(client):
    response = client.get(
        "/logout",
        headers={"Authorization": f"Bearer {_token(role='regular')}"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
