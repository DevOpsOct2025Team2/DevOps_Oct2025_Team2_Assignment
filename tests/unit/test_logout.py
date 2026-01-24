import pytest
from flask import session

AUTH_LOGOUT_PATH = "/api/v1/auth/logout"

@pytest.fixture(autouse=True)
def bypass_login(monkeypatch):
    import app.security
    monkeypatch.setattr(app.security, "login_required", lambda f: f)

@pytest.fixture
def unwrapped_logout(client):
    import app.routes.api as api_module

    unwrapped = getattr(api_module.logout, "__wrapped__", api_module.logout)
    for rule in client.application.url_map.iter_rules():
        if rule.rule.rstrip("/") == AUTH_LOGOUT_PATH:
            client.application.view_functions[rule.endpoint] = unwrapped
            break

def test_logout_clears_session_and_cookies(client, unwrapped_logout):
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    client.set_cookie("access_token")

    response = client.post(AUTH_LOGOUT_PATH, follow_redirects=True)

    assert response.status_code in (200, 302)
    with client.session_transaction() as sess:
        assert "user_id" not in sess

    set_cookie = response.headers.get("Set-Cookie", "")
    assert "access_token=" in set_cookie
    assert ("access_token=;" in set_cookie) or ("expires=" in set_cookie.lower())