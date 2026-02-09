import pytest
from pytest_bdd import scenarios, given, when, then, parsers

import app.services.auth_service as auth_service
from app.services.user_service import UserService

scenarios("../features/admin.feature")


@pytest.fixture
def api_response():
    return {}


@pytest.fixture
def create_payload():
    return {"username": "", "password": "", "role": "regular"}


def _set_auth_cookie(client, app, token):
    cookie_name = app.config.get("AUTH_COOKIE_NAME", "access_token")
    client.set_cookie(cookie_name, token, domain="localhost", path="/")


@given(parsers.parse('an authenticated user with role "{role}"'))
def given_authenticated_user(client, app, role):
    role_value = (role or "").strip().lower()
    token = auth_service.create_access_token(
        {"id": "admin-1", "username": "admin", "role": role_value},
        app.config,
    )
    _set_auth_cookie(client, app, token)


@given("the user service returns a user list")
def mock_user_list(monkeypatch):
    def fake_init(self):
        self.supabase = object()

    def fake_get_all_users(self, *args, **kwargs):
        return {
            "users": [
                {"id": "user-1", "username": "alice", "role": "regular"},
                {"id": "user-2", "username": "bob", "role": "regular"},
            ],
            "page": 1,
            "per_page": 10,
            "total": 2,
        }

    monkeypatch.setattr(UserService, "__init__", fake_init)
    monkeypatch.setattr(UserService, "get_all_users", fake_get_all_users)


@given(parsers.parse('a new user payload with username "{username}" and password "{password}"'))
def given_new_user_payload(create_payload, username, password):
    create_payload["username"] = username
    create_payload["password"] = password


@given("the database accepts the new user")
def mock_create_user_db(monkeypatch):
    class _FakeTable:
        def insert(self, data):
            return self

        def execute(self):
            return {"data": [{"id": "user-3"}]}

    class _FakeSupabase:
        def table(self, name):
            return _FakeTable()

    monkeypatch.setattr(auth_service, "get_supabase_client", lambda: _FakeSupabase())
    monkeypatch.setattr(auth_service, "hash_password", lambda password: "hashed")


@given(parsers.parse('a target user id "{user_id}"'))
def given_target_user_id(api_response, user_id):
    api_response["target_user_id"] = user_id


@given("the user exists in the system")
def mock_user_exists(monkeypatch):
    def fake_init(self):
        self.supabase = object()

    def fake_get_user_by_id(self, user_id):
        return {"id": user_id, "username": "someone", "role": "regular"}

    def fake_delete_user_by_id(self, user_id):
        return {"id": user_id, "username": "someone", "role": "regular"}

    monkeypatch.setattr(UserService, "__init__", fake_init)
    monkeypatch.setattr(UserService, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(UserService, "delete_user_by_id", fake_delete_user_by_id)


@when("I request the admin user list")
def when_request_user_list(client, api_response):
    api_response["response"] = client.get("/api/v1/admin/users")


@when("I submit an admin create user request")
def when_create_user(client, api_response, create_payload):
    api_response["response"] = client.post("/api/v1/auth/users", json=create_payload)


@when("I submit an admin delete user request")
def when_delete_user(client, api_response):
    user_id = api_response.get("target_user_id", "")
    api_response["response"] = client.delete(f"/api/v1/admin/users/{user_id}")


@then(parsers.parse("the response status should be {status:d}"))
def then_status(api_response, status):
    response = api_response["response"]
    assert response.status_code == status


@then("the response should include users")
def then_response_includes_users(api_response):
    data = api_response["response"].get_json()
    assert "users" in data
    assert isinstance(data["users"], list)
