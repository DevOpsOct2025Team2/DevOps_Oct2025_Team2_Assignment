import datetime
from unittest.mock import MagicMock, patch

import jwt
import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "test-secret"
    with app.test_client() as client:
        yield client


def _token(role="admin", user_id="admin-1", username="admin_user"):
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "app_metadata": {"role": role},
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def _valid_payload():
    return {"username": "new_user", "password": "Password123", "role": "regular"}


def test_create_user_success(client):
    token = _token(role="admin")
    payload = _valid_payload()
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

    with patch("app.routes.api.auth_service.get_supabase_client", return_value=mock_supabase):
        with patch("app.routes.api.auth_service.hash_password", return_value="hashed-password"):
            response = client.post(
                "/api/v1/auth/users",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 201
    assert response.get_json()["message"] == "User created successfully."


def test_create_user_missing_auth_token(client):
    response = client.post("/api/v1/auth/users", json=_valid_payload())
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorized"


def test_create_user_non_admin_forbidden(client):
    token = _token(role="regular", user_id="regular-1", username="regular_user")
    response = client.post(
        "/api/v1/auth/users",
        json=_valid_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "Unauthorized"


def test_create_user_missing_body(client):
    token = _token(role="admin")
    response = client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Request body required"


def test_create_user_username_too_short(client):
    token = _token(role="admin")
    payload = _valid_payload()
    payload["username"] = "ab"
    response = client.post(
        "/api/v1/auth/users",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "3-32 characters" in response.get_json()["error"]


def test_create_user_username_invalid_chars(client):
    token = _token(role="admin")
    payload = _valid_payload()
    payload["username"] = "bad user!"
    response = client.post(
        "/api/v1/auth/users",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "letters, numbers, and underscores" in response.get_json()["error"]


def test_create_user_password_too_short(client):
    token = _token(role="admin")
    payload = _valid_payload()
    payload["password"] = "Pass1"
    response = client.post(
        "/api/v1/auth/users",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "at least 8 characters" in response.get_json()["error"]


def test_create_user_password_missing_numeric_or_alpha(client):
    token = _token(role="admin")
    payload = _valid_payload()
    payload["password"] = "allletters"
    response = client.post(
        "/api/v1/auth/users",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "at least 8 characters with letters and numbers" in response.get_json()["error"]


def test_create_user_invalid_role(client):
    token = _token(role="admin")
    payload = _valid_payload()
    payload["role"] = "superadmin"
    response = client.post(
        "/api/v1/auth/users",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "Invalid role" in response.get_json()["error"]


def test_create_user_database_unavailable(client):
    token = _token(role="admin")
    with patch("app.routes.api.auth_service.get_supabase_client", return_value=None):
        response = client.post(
            "/api/v1/auth/users",
            json=_valid_payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 500
    assert response.get_json()["error"] == "Database service unavailable."


def test_create_user_password_hashing_failure(client):
    token = _token(role="admin")
    mock_supabase = MagicMock()
    with patch("app.routes.api.auth_service.get_supabase_client", return_value=mock_supabase):
        with patch("app.routes.api.auth_service.hash_password", side_effect=Exception("hash fail")):
            response = client.post(
                "/api/v1/auth/users",
                json=_valid_payload(),
                headers={"Authorization": f"Bearer {token}"},
            )
    assert response.status_code == 500
    assert response.get_json()["error"] == "Failed to process password."


def test_create_user_duplicate_username_conflict(client):
    token = _token(role="admin")
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
        "duplicate key value"
    )

    with patch("app.routes.api.auth_service.get_supabase_client", return_value=mock_supabase):
        with patch("app.routes.api.auth_service.hash_password", return_value="hashed-password"):
            response = client.post(
                "/api/v1/auth/users",
                json=_valid_payload(),
                headers={"Authorization": f"Bearer {token}"},
            )
    assert response.status_code == 409
    assert response.get_json()["error"] == "Username already exists."


def test_create_user_insert_generic_error(client):
    token = _token(role="admin")
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("timeout")

    with patch("app.routes.api.auth_service.get_supabase_client", return_value=mock_supabase):
        with patch("app.routes.api.auth_service.hash_password", return_value="hashed-password"):
            response = client.post(
                "/api/v1/auth/users",
                json=_valid_payload(),
                headers={"Authorization": f"Bearer {token}"},
            )
    assert response.status_code == 500
    assert response.get_json()["error"] == "Failed to create user in database."
