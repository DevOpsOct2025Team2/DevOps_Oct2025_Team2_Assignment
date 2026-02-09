"""Integration tests for GET /api/v1/files/<file_id>/download endpoint.

Covers:
- Authentication enforcement (missing / expired token → 401)
- RBAC enforcement (admin role → 403)
- Ownership verification (other user's file → 403)
- File not found → 404
- Successful download by file owner → 200 with binary content
- Audit logging of unauthorized attempts
"""

import datetime
import io
from datetime import timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest

from app import create_app


@pytest.fixture
def app():
    app = create_app("testing")
    app.config.update(
        JWT_SECRET_KEY="test-secret",
        JWT_ACCESS_TOKEN_EXPIRES=3600,
        AUTH_COOKIE_NAME="access_token",
        AUTH_COOKIE_SECURE=False,
        AUTH_COOKIE_SAMESITE="Lax",
    )
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def _generate_token(
    role, secret="test-secret", user_id="test-user", username="testuser", expired=False
):
    """Helper to create a JWT token for tests."""
    if expired:
        exp = datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=1)
    else:
        exp = datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=1)

    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "iat": int(datetime.datetime.now(timezone.utc).timestamp()),
        "exp": exp,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------


class TestDownloadAuthentication:
    """Requests without a valid token must be rejected."""

    def test_no_token_returns_401(self, client):
        response = client.get("/api/v1/files/file1/download")
        assert response.status_code == 401

    def test_expired_token_returns_401(self, client):
        token = _generate_token("regular", user_id="user1", expired=True)
        response = client.get(
            "/api/v1/files/file1/download",
            headers=_auth_header(token),
        )
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client):
        response = client.get(
            "/api/v1/files/file1/download",
            headers={"Authorization": "Bearer this.is.garbage"},
        )
        assert response.status_code == 401

    def test_wrong_secret_returns_401(self, client):
        token = _generate_token("regular", secret="wrong-secret", user_id="user1")
        response = client.get(
            "/api/v1/files/file1/download",
            headers=_auth_header(token),
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# RBAC tests
# ---------------------------------------------------------------------------


class TestDownloadRBAC:
    """Only users with the 'regular' role may access the download endpoint."""

    def test_admin_forbidden(self, client):
        token = _generate_token("admin", user_id="admin1", username="admin_user")
        response = client.get(
            "/api/v1/files/file1/download",
            headers=_auth_header(token),
        )
        assert response.status_code == 403
        data = response.get_json()
        assert data is not None
        assert "error" in data

    @patch("app.security.jwt.decode")
    def test_unknown_role_forbidden(self, mock_jwt_decode, client):
        token = _generate_token("manager", user_id="mgr1", username="mgr_user")
        mock_jwt_decode.return_value = {
            "sub": "mgr1",
            "id": "mgr1",
            "role": "manager",
            "username": "mgr_user",
        }
        response = client.get(
            "/api/v1/files/file1/download",
            headers=_auth_header(token),
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Ownership verification tests
# ---------------------------------------------------------------------------


class TestDownloadOwnership:
    """A regular user must only download their own files."""

    @patch("app.security.jwt.decode")
    @patch("app.routes.api.FileService")
    @patch("app.routes.api.auth_service.get_supabase_client")
    def test_other_users_file_returns_403(
        self, mock_get_client, MockFileService, mock_jwt_decode, client
    ):
        token = _generate_token("regular", user_id="user1")
        mock_jwt_decode.return_value = {
            "sub": "user1",
            "id": "user1",
            "role": "regular",
            "username": "testuser",
        }
        mock_get_client.return_value = MagicMock()
        MockFileService.return_value.get_file_for_download.return_value = {
            "error": "You do not have permission to download this file",
            "forbidden": True,
        }

        response = client.get(
            "/api/v1/files/other_user_file/download",
            headers=_auth_header(token),
        )

        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == "forbidden"
        assert "permission" in data["message"].lower()

    @patch("app.security.jwt.decode")
    @patch("app.routes.api.FileService")
    @patch("app.routes.api.auth_service.get_supabase_client")
    def test_ownership_verified_with_correct_user_id(
        self, mock_get_client, MockFileService, mock_jwt_decode, client
    ):
        """FileService.get_file_for_download is called with the authenticated user's id."""
        token = _generate_token("regular", user_id="user42")
        mock_jwt_decode.return_value = {
            "sub": "user42",
            "id": "user42",
            "role": "regular",
            "username": "user42name",
        }
        mock_get_client.return_value = MagicMock()

        file_content = b"file bytes here"
        MockFileService.return_value.get_file_for_download.return_value = {
            "file_bytes": file_content,
            "filename": "test.txt",
            "file_type": "text/plain",
            "file_size": len(file_content),
        }

        response = client.get(
            "/api/v1/files/fileXYZ/download",
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        MockFileService.return_value.get_file_for_download.assert_called_once_with(
            user_id="user42", file_id="fileXYZ"
        )


# ---------------------------------------------------------------------------
# File not found tests
# ---------------------------------------------------------------------------


class TestDownloadNotFound:
    @patch("app.security.jwt.decode")
    @patch("app.routes.api.FileService")
    @patch("app.routes.api.auth_service.get_supabase_client")
    def test_nonexistent_file_returns_404(
        self, mock_get_client, MockFileService, mock_jwt_decode, client
    ):
        token = _generate_token("regular", user_id="user1")
        mock_jwt_decode.return_value = {
            "sub": "user1",
            "id": "user1",
            "role": "regular",
            "username": "testuser",
        }
        mock_get_client.return_value = MagicMock()
        MockFileService.return_value.get_file_for_download.return_value = {
            "error": "File not found",
        }

        response = client.get(
            "/api/v1/files/nonexistent/download",
            headers=_auth_header(token),
        )

        assert response.status_code == 404
        data = response.get_json()
        assert "not_found" in data.get("error", "")


# ---------------------------------------------------------------------------
# Successful download tests
# ---------------------------------------------------------------------------


class TestDownloadSuccess:
    @patch("app.security.jwt.decode")
    @patch("app.routes.api.FileService")
    @patch("app.routes.api.auth_service.get_supabase_client")
    def test_successful_download_returns_binary(
        self, mock_get_client, MockFileService, mock_jwt_decode, client
    ):
        token = _generate_token("regular", user_id="user1")
        mock_jwt_decode.return_value = {
            "sub": "user1",
            "id": "user1",
            "role": "regular",
            "username": "testuser",
        }
        mock_get_client.return_value = MagicMock()

        file_content = b"%PDF-1.4 some pdf content"
        MockFileService.return_value.get_file_for_download.return_value = {
            "file_bytes": file_content,
            "filename": "report.pdf",
            "file_type": "application/pdf",
            "file_size": len(file_content),
        }

        response = client.get(
            "/api/v1/files/file1/download",
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        assert response.data == file_content
        assert response.content_type == "application/pdf"
        # Check content-disposition signals an attachment download
        cd = response.headers.get("Content-Disposition", "")
        assert "attachment" in cd
        assert "report.pdf" in cd

    @patch("app.security.jwt.decode")
    @patch("app.routes.api.FileService")
    @patch("app.routes.api.auth_service.get_supabase_client")
    def test_download_image_file(
        self, mock_get_client, MockFileService, mock_jwt_decode, client
    ):
        token = _generate_token("regular", user_id="user1")
        mock_jwt_decode.return_value = {
            "sub": "user1",
            "id": "user1",
            "role": "regular",
            "username": "testuser",
        }
        mock_get_client.return_value = MagicMock()

        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        MockFileService.return_value.get_file_for_download.return_value = {
            "file_bytes": fake_png,
            "filename": "photo.png",
            "file_type": "image/png",
            "file_size": len(fake_png),
        }

        response = client.get(
            "/api/v1/files/img1/download",
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        assert response.data == fake_png
        assert "image/png" in response.content_type

    @patch("app.security.jwt.decode")
    @patch("app.routes.api.FileService")
    @patch("app.routes.api.auth_service.get_supabase_client")
    def test_download_via_cookie_auth(
        self, mock_get_client, MockFileService, mock_jwt_decode, app, client
    ):
        """Download also works when the token is in an httpOnly cookie."""
        token = _generate_token("regular", user_id="user1")
        mock_jwt_decode.return_value = {
            "sub": "user1",
            "id": "user1",
            "role": "regular",
            "username": "testuser",
        }
        mock_get_client.return_value = MagicMock()

        file_content = b"cookie auth content"
        MockFileService.return_value.get_file_for_download.return_value = {
            "file_bytes": file_content,
            "filename": "cookie.txt",
            "file_type": "text/plain",
            "file_size": len(file_content),
        }

        client.set_cookie("access_token", token, domain="localhost")
        response = client.get("/api/v1/files/fileCookie/download")

        assert response.status_code == 200
        assert response.data == file_content


# ---------------------------------------------------------------------------
# Storage / service error tests
# ---------------------------------------------------------------------------


class TestDownloadServiceErrors:
    @patch("app.security.jwt.decode")
    @patch("app.routes.api.FileService")
    @patch("app.routes.api.auth_service.get_supabase_client")
    def test_storage_error_returns_500(
        self, mock_get_client, MockFileService, mock_jwt_decode, client
    ):
        token = _generate_token("regular", user_id="user1")
        mock_jwt_decode.return_value = {
            "sub": "user1",
            "id": "user1",
            "role": "regular",
            "username": "testuser",
        }
        mock_get_client.return_value = MagicMock()
        MockFileService.return_value.get_file_for_download.return_value = {
            "error": "Failed to download file from storage",
        }

        response = client.get(
            "/api/v1/files/file1/download",
            headers=_auth_header(token),
        )

        assert response.status_code == 500
        data = response.get_json()
        assert "download_failed" in data.get("error", "")

    @patch("app.security.jwt.decode")
    @patch("app.routes.api.FileService")
    @patch("app.routes.api.auth_service.get_supabase_client")
    def test_supabase_client_none_returns_500(
        self, mock_get_client, MockFileService, mock_jwt_decode, client
    ):
        token = _generate_token("regular", user_id="user1")
        mock_jwt_decode.return_value = {
            "sub": "user1",
            "id": "user1",
            "role": "regular",
            "username": "testuser",
        }
        mock_get_client.return_value = None

        response = client.get(
            "/api/v1/files/file1/download",
            headers=_auth_header(token),
        )

        assert response.status_code == 500
        data = response.get_json()
        assert "unavailable" in data.get("error", "").lower() or "Database" in data.get(
            "error", ""
        )

    @patch("app.security.jwt.decode")
    @patch("app.routes.api.FileService")
    @patch("app.routes.api.auth_service.get_supabase_client")
    def test_unexpected_exception_returns_500(
        self, mock_get_client, MockFileService, mock_jwt_decode, client
    ):
        token = _generate_token("regular", user_id="user1")
        mock_jwt_decode.return_value = {
            "sub": "user1",
            "id": "user1",
            "role": "regular",
            "username": "testuser",
        }
        mock_get_client.return_value = MagicMock()
        MockFileService.return_value.get_file_for_download.side_effect = RuntimeError(
            "boom"
        )

        response = client.get(
            "/api/v1/files/file1/download",
            headers=_auth_header(token),
        )

        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Audit logging tests
# ---------------------------------------------------------------------------


class TestDownloadAuditLogging:
    @patch("app.routes.api.audit_logger")
    @patch("app.security.jwt.decode")
    @patch("app.routes.api.FileService")
    @patch("app.routes.api.auth_service.get_supabase_client")
    def test_forbidden_download_is_logged(
        self, mock_get_client, MockFileService, mock_jwt_decode, mock_audit, client
    ):
        token = _generate_token("regular", user_id="user1", username="badactor")
        mock_jwt_decode.return_value = {
            "sub": "user1",
            "id": "user1",
            "role": "regular",
            "username": "badactor",
        }
        mock_get_client.return_value = MagicMock()
        MockFileService.return_value.get_file_for_download.return_value = {
            "error": "You do not have permission to download this file",
            "forbidden": True,
        }

        client.get(
            "/api/v1/files/secret_file/download",
            headers=_auth_header(token),
        )

        # At least one warning-level audit log call should mention the unauthorized download
        warning_calls = [str(c) for c in mock_audit.warning.call_args_list]
        assert any("UNAUTHORIZED DOWNLOAD" in c for c in warning_calls), (
            f"Expected 'UNAUTHORIZED DOWNLOAD' in audit warnings, got: {warning_calls}"
        )

    @patch("app.routes.api.audit_logger")
    @patch("app.security.jwt.decode")
    @patch("app.routes.api.FileService")
    @patch("app.routes.api.auth_service.get_supabase_client")
    def test_successful_download_is_logged(
        self, mock_get_client, MockFileService, mock_jwt_decode, mock_audit, client
    ):
        token = _generate_token("regular", user_id="user1", username="gooduser")
        mock_jwt_decode.return_value = {
            "sub": "user1",
            "id": "user1",
            "role": "regular",
            "username": "gooduser",
        }
        mock_get_client.return_value = MagicMock()
        MockFileService.return_value.get_file_for_download.return_value = {
            "file_bytes": b"data",
            "filename": "ok.txt",
            "file_type": "text/plain",
            "file_size": 4,
        }

        client.get(
            "/api/v1/files/file1/download",
            headers=_auth_header(token),
        )

        info_calls = [str(c) for c in mock_audit.info.call_args_list]
        assert any("downloaded" in c.lower() for c in info_calls), (
            f"Expected 'downloaded' in audit info logs, got: {info_calls}"
        )

    @patch("app.routes.api.audit_logger")
    def test_admin_download_attempt_is_logged(self, mock_audit, client):
        token = _generate_token("admin", user_id="admin1", username="admin_user")
        client.get(
            "/api/v1/files/file1/download",
            headers=_auth_header(token),
        )

        warning_calls = [str(c) for c in mock_audit.warning.call_args_list]
        assert any("admin" in c.lower() or "Non-regular" in c for c in warning_calls), (
            f"Expected admin attempt logged in audit warnings, got: {warning_calls}"
        )
