import pytest
from pytest_bdd import scenarios, given, when, then, parsers

import app.services.auth_service as auth_service

scenarios("../features/login.feature")


@pytest.fixture
def login_payload():
    return {"username": "", "password": ""}


@pytest.fixture
def api_response():
    return {}


@given(parsers.re(r'^a login username "(?P<username>.*)" and password "(?P<password>.*)"$'))
def set_login_payload(login_payload, username, password):
    login_payload["username"] = username
    login_payload["password"] = password


@given(parsers.parse('the auth service recognizes this user as role "{role}"'))
def mock_auth_service_accept(monkeypatch, login_payload, role):
    def fake_authenticate_user(username, password):
        if username == login_payload["username"] and password == login_payload["password"]:
            return {
                "id": "user-1",
                "username": username,
                "role": role,
                "is_active": True,
            }
        return None

    monkeypatch.setattr(auth_service, "authenticate_user", fake_authenticate_user)


@given("the auth service rejects the credentials")
def mock_auth_service_reject(monkeypatch):
    def fake_authenticate_user(username, password):
        return None

    monkeypatch.setattr(auth_service, "authenticate_user", fake_authenticate_user)


@given("the auth service is misconfigured")
def mock_auth_service_error(monkeypatch):
    def fake_authenticate_user(username, password):
        raise RuntimeError("Auth not configured")

    monkeypatch.setattr(auth_service, "authenticate_user", fake_authenticate_user)


@given("no login payload")
def clear_login_payload(login_payload):
    login_payload.clear()


@when("I submit a login request")
def submit_login_request(client, login_payload, api_response):
    api_response["response"] = client.post("/api/v1/auth/login", json=login_payload)


@when("I submit a login request without json")
def submit_login_request_no_json(client, api_response):
    api_response["response"] = client.post("/api/v1/auth/login")


@then(parsers.parse("the response status should be {status:d}"))
def assert_status(api_response, status):
    response = api_response["response"]
    assert response.status_code == status


@then(parsers.parse('the response role should be "{role}"'))
def assert_role(api_response, role):
    data = api_response["response"].get_json()
    assert data["role"] == role


@then(parsers.parse('the response redirect_to should be "{path}"'))
def assert_redirect(api_response, path):
    data = api_response["response"].get_json()
    assert data["redirect_to"] == path


@then(parsers.parse('the response error should be "{error}"'))
def assert_error(api_response, error):
    data = api_response["response"].get_json()
    assert data["error"] == error


@then("the auth cookie should be set with security attributes")
def assert_cookie_security(api_response, app):
    response = api_response["response"]
    cookie_name = app.config.get("AUTH_COOKIE_NAME", "access_token")
    set_cookies = response.headers.getlist("Set-Cookie")
    cookie_header = ""
    for header in set_cookies:
        if header.startswith(f"{cookie_name}="):
            cookie_header = header
            break
    assert cookie_header, f"Expected Set-Cookie for {cookie_name}"
    assert "HttpOnly" in cookie_header
    assert "SameSite=Lax" in cookie_header
    assert "Path=/" in cookie_header
    assert "Max-Age=" in cookie_header
