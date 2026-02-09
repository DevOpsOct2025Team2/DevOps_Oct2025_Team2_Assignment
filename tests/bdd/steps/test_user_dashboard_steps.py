import io

import pytest
from pytest_bdd import scenarios, given, when, then, parsers

import app.services.auth_service as auth_service
from app.services.file_service import FileService

scenarios("../features/user_dashboard.feature")


@pytest.fixture
def api_response():
    return {}


def _set_auth_cookie(client, app, token):
    cookie_name = app.config.get("AUTH_COOKIE_NAME", "access_token")
    client.set_cookie(cookie_name, token, domain="localhost", path="/")


@given("an unauthenticated user")
def given_unauthenticated_user(client, app):
    cookie_name = app.config.get("AUTH_COOKIE_NAME", "access_token")
    try:
        client.delete_cookie("localhost", cookie_name, path="/")
    except TypeError:
        # Older Flask test client signature
        client.delete_cookie(cookie_name, domain="localhost", path="/")


@given(parsers.parse('an authenticated user with role "{role}" and id "{user_id}"'))
def given_authenticated_user(client, app, role, user_id):
    role_value = (role or "").strip().lower()
    token = auth_service.create_access_token(
        {"id": user_id, "username": "tester", "role": role_value},
        app.config,
    )
    _set_auth_cookie(client, app, token)


@given("the file service returns a file list")
def mock_file_list(monkeypatch):
    def fake_init(self, supabase_client=None):
        self.supabase = object()

    def fake_get_user_files(self, *args, **kwargs):
        return {
            "files": [
                {"id": "file-1", "filename": "doc.txt", "file_size": 12, "file_type": "text/plain"},
                {"id": "file-2", "filename": "img.png", "file_size": 64, "file_type": "image/png"},
            ],
            "page": 1,
            "per_page": 10,
            "total": 2,
        }

    monkeypatch.setattr(FileService, "__init__", fake_init)
    monkeypatch.setattr(FileService, "get_user_files", fake_get_user_files)


@given("the file service accepts uploads")
def mock_file_upload(monkeypatch):
    def fake_init(self, supabase_client=None):
        self.supabase = object()

    def fake_upload_file(self, *args, **kwargs):
        return {"id": "file-1", "filename": "test.txt", "file_size": 4, "file_type": "text/plain"}

    monkeypatch.setattr(FileService, "__init__", fake_init)
    monkeypatch.setattr(FileService, "upload_file", fake_upload_file)


@given(parsers.parse('the file service allows deleting file "{file_id}"'))
def mock_file_delete(monkeypatch, file_id):
    expected_file_id = file_id
    def fake_init(self, supabase_client=None):
        self.supabase = object()

    def fake_delete_file(self, user_id, file_id=None, target_file_id=None):
        target = file_id if file_id is not None else target_file_id
        if target == expected_file_id:
            return {"success": True, "message": "File deleted successfully"}
        return {"error": "Unauthorized"}

    monkeypatch.setattr(FileService, "__init__", fake_init)
    monkeypatch.setattr(FileService, "delete_file", fake_delete_file)


@when("I request my file list")
def when_request_file_list(client, api_response):
    api_response["response"] = client.get("/api/v1/files/me")


@when(parsers.parse('I upload a file named "{filename}"'))
def when_upload_file(client, api_response, filename):
    data = {"file": (io.BytesIO(b"test"), filename)}
    api_response["response"] = client.post(
        "/api/v1/files/upload",
        data=data,
        content_type="multipart/form-data",
    )


@when(parsers.parse('I delete my file "{file_id}"'))
def when_delete_file(client, api_response, file_id):
    api_response["response"] = client.delete(f"/api/v1/files/{file_id}")


@then(parsers.parse("the response status should be {status:d}"))
def then_status(api_response, status):
    response = api_response["response"]
    assert response.status_code == status


@then("the response should include files")
def then_response_includes_files(api_response):
    data = api_response["response"].get_json()
    assert "files" in data
    assert isinstance(data["files"], list)
