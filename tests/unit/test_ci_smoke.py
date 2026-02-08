import datetime
from unittest.mock import patch

import jwt

from app import create_app


def _admin_token():
    payload = {
        "sub": "admin-ci",
        "username": "ci_admin",
        "role": "admin",
        "app_metadata": {"role": "admin"},
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")


def test_ci_delete_user_endpoint_smoke():
    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "test-secret"
    client = app.test_client()
    token = _admin_token()

    with patch("app.routes.api.UserService") as mock_service:
        mock_instance = mock_service.return_value
        mock_instance.get_user_by_id.return_value = {"id": "user-ci-1", "username": "ci_user"}
        mock_instance.delete_user_by_id.return_value = {"id": "user-ci-1", "username": "ci_user"}

        response = client.delete(
            "/api/v1/admin/users/user-ci-1",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.get_json()["message"] == "User deleted successfully."
