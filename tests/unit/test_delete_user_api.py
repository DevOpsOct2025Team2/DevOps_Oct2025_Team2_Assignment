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


def generate_token(role, user_id="admin-1", username="admin"):
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "app_metadata": {"role": role},
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def test_delete_user_forbidden_for_non_admin(client):
    token = generate_token("regular", user_id="regular-1", username="regular_user")
    response = client.delete(
        "/api/v1/admin/users/target-user",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Unauthorized"


def test_delete_user_blocks_self_delete(client):
    token = generate_token("admin", user_id="admin-1", username="admin_user")
    response = client.delete(
        "/api/v1/admin/users/admin-1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "cannot delete your own account" in response.get_json()["error"].lower()


def test_delete_user_returns_not_found_when_missing_user(client):
    token = generate_token("admin")
    with patch("app.routes.api.UserService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.get_user_by_id.return_value = None

        response = client.delete(
            "/api/v1/admin/users/missing-user",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert response.get_json()["error"] == "User not found."
        mock_instance.delete_user_by_id.assert_not_called()


def test_delete_user_success(client):
    token = generate_token("admin", user_id="admin-1", username="admin_user")
    with patch("app.routes.api.UserService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.get_user_by_id.return_value = {
            "id": "user-99",
            "username": "target_user",
            "role": "regular",
            "is_active": True,
        }
        mock_instance.delete_user_by_id.return_value = {"id": "user-99", "username": "target_user"}

        response = client.delete(
            "/api/v1/admin/users/user-99",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.get_json()["message"] == "User deleted successfully."
        mock_instance.get_user_by_id.assert_called_once_with("user-99")
        mock_instance.delete_user_by_id.assert_called_once_with("user-99")


def test_delete_user_returns_server_error_on_failed_delete(client):
    token = generate_token("admin")
    with patch("app.routes.api.UserService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.get_user_by_id.return_value = {"id": "user-10", "username": "ten"}
        mock_instance.delete_user_by_id.return_value = None

        response = client.delete(
            "/api/v1/admin/users/user-10",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 500
        assert response.get_json()["error"] == "Failed to delete user."
