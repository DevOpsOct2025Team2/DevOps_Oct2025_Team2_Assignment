from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from app.services.auth_service import create_access_token

scenarios("../features/logout.feature")


@pytest.fixture
def api_response():
    return {}


def _set_auth_cookie(client, app, token):
    cookie_name = app.config.get("AUTH_COOKIE_NAME", "access_token")
    client.set_cookie(cookie_name, token, domain="localhost", path="/")


def _clear_auth_cookie(client, app):
    cookie_name = app.config.get("AUTH_COOKIE_NAME", "access_token")
    client.delete_cookie(cookie_name, domain="localhost", path="/")


def _find_cookie(headers, cookie_name):
    for header in headers:
        if header.startswith(f"{cookie_name}="):
            return header
    return ""


@given(parsers.parse('an authenticated user with role "{role}"'))
def given_authenticated_user(client, app, role):
    role_value = (role or "").strip().lower()
    token = create_access_token(
        {
            "id": "user-1",
            "username": "tester",
            "role": role_value,
        },
        app.config,
    )
    _set_auth_cookie(client, app, token)


@given("no authentication")
def given_no_authentication(client, app):
    _clear_auth_cookie(client, app)


@given("an invalid auth token")
def given_invalid_token(client, app):
    _set_auth_cookie(client, app, "not-a-valid-jwt")


@given("an expired auth token")
def given_expired_token(client, app):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "user-1",
        "username": "tester",
        "role": "regular",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    token = jwt.encode(payload, app.config["JWT_SECRET_KEY"], algorithm="HS256")
    _set_auth_cookie(client, app, token)


@when("I submit a logout request")
def when_submit_logout(client, api_response):
    api_response["response"] = client.post("/api/v1/auth/logout")


@then(parsers.parse("the response status should be {status:d}"))
def then_status(api_response, status):
    response = api_response["response"]
    assert response.status_code == status


@then(parsers.parse('the response redirect_to should be "{path}"'))
def then_redirect_to(api_response, path):
    data = api_response["response"].get_json()
    assert data["redirect_to"] == path


@then(parsers.parse('the response error should be "{error}"'))
def then_error(api_response, error):
    data = api_response["response"].get_json()
    assert data["error"] == error


@then("the auth cookie should be cleared")
def then_cookie_cleared(api_response, app):
    response = api_response["response"]
    cookie_name = app.config.get("AUTH_COOKIE_NAME", "access_token")
    set_cookies = response.headers.getlist("Set-Cookie")
    cookie_header = _find_cookie(set_cookies, cookie_name)
    assert cookie_header, f"Expected Set-Cookie for {cookie_name}"
    assert "Max-Age=0" in cookie_header or "Expires=" in cookie_header
