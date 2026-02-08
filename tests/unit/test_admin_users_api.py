import datetime
from unittest.mock import patch

import jwt
import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "test-secret"
    with app.test_client() as client:
        yield client


def _token(role="admin", user_id="admin-1", username="admin"):
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "app_metadata": {"role": role},
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def test_get_admin_users_requires_authentication(client):
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorized"


def test_get_admin_users_forbidden_for_non_admin(client):
    response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {_token(role='regular', user_id='u-1', username='regular')}"},
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "Unauthorized"


def test_get_admin_users_success(client):
    mock_result = {
        "users": [{"id": "u1", "username": "alice", "role": "regular", "created_at": "2025-01-01", "is_active": True}],
        "page": 2,
        "per_page": 10,
        "total": 25,
    }
    with patch("app.routes.api.UserService") as mock_service:
        mock_service.return_value.get_all_users.return_value = mock_result
        response = client.get(
            "/api/v1/admin/users?page=2&per_page=10&search=ali&sort_by=username&order=asc",
            headers={"Authorization": f"Bearer {_token(role='admin')}"},
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 25
    assert data["page"] == 2
    assert data["users"][0]["username"] == "alice"


def test_get_admin_users_returns_500_when_service_reports_error(client):
    with patch("app.routes.api.UserService") as mock_service:
        mock_service.return_value.get_all_users.return_value = {"error": "database timeout"}
        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {_token(role='admin')}"},
        )

    assert response.status_code == 500
    assert response.get_json()["message"] == "database timeout"


def test_get_admin_users_returns_500_on_unexpected_exception(client):
    with patch("app.routes.api.UserService", side_effect=Exception("boom")):
        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {_token(role='admin')}"},
        )

    assert response.status_code == 500
    assert response.get_json()["message"] == "Failed to fetch users"
