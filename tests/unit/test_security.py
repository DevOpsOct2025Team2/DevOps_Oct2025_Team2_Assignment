import jwt
import pytest
from flask import Flask, g, jsonify

import app.security as security_module
from app.security import _get_token, _wants_json, login_required, role_required


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret"
    app.config["JWT_SECRET_KEY"] = "test-secret"
    app.config["AUTH_COOKIE_NAME"] = "access_token"

    app.add_url_rule("/login", endpoint="main.login", view_func=lambda: "login")
    app.add_url_rule("/admin", endpoint="main.admin", view_func=lambda: "admin")
    app.add_url_rule("/dashboard", endpoint="main.dashboard", view_func=lambda: "dashboard")

    @app.route("/api/protected")
    @login_required
    def api_protected():
        return jsonify({"user": g.current_user})

    @app.route("/api/admin-only")
    @login_required
    @role_required("admin")
    def api_admin_only():
        return jsonify({"ok": True})

    @app.route("/page/admin-only")
    @login_required
    @role_required("admin")
    def page_admin_only():
        return "ok"

    return app


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


def test_get_token_prefers_cookie_over_authorization_header(app):
    with app.test_request_context(
        "/api/protected",
        headers={"Authorization": "Bearer header-token", "Cookie": "access_token=cookie-token"},
    ):
        assert _get_token() == "cookie-token"


def test_get_token_reads_authorization_header_when_cookie_missing(app):
    with app.test_request_context(
        "/api/protected",
        headers={"Authorization": "Bearer header-token"},
    ):
        assert _get_token() == "header-token"


def test_get_token_returns_none_when_not_present(app):
    with app.test_request_context("/api/protected"):
        assert _get_token() is None


def test_wants_json_true_for_api_paths(app):
    with app.test_request_context("/api/protected"):
        assert _wants_json() is True


def test_wants_json_true_for_json_accept_header(app):
    with app.test_request_context("/page/admin-only", headers={"Accept": "application/json"}):
        assert _wants_json() is True


def test_login_required_returns_401_without_token(client):
    response = client.get("/api/protected")
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "unauthorized"


def test_login_required_returns_401_with_invalid_token(client, monkeypatch):
    def _raise_invalid(_token, _config):
        raise jwt.InvalidTokenError("bad token")

    monkeypatch.setattr(security_module, "decode_access_token", _raise_invalid)
    response = client.get("/api/protected", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "unauthorized"


def test_login_required_sets_g_current_user_on_success(client, monkeypatch):
    payload = {"sub": "user-1", "username": "alice", "role": "regular"}
    monkeypatch.setattr(security_module, "decode_access_token", lambda _token, _config: payload)

    response = client.get("/api/protected", headers={"Authorization": "Bearer valid"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["user"]["username"] == "alice"


def test_role_required_returns_403_for_api_when_role_not_allowed(client, monkeypatch):
    payload = {"sub": "user-1", "username": "alice", "role": "regular"}
    monkeypatch.setattr(security_module, "decode_access_token", lambda _token, _config: payload)

    response = client.get("/api/admin-only", headers={"Authorization": "Bearer valid"})
    assert response.status_code == 403
    data = response.get_json()
    assert data["error"] == "forbidden"


def test_role_required_redirects_for_html_when_role_not_allowed(client, monkeypatch):
    payload = {"sub": "user-1", "username": "alice", "role": "regular"}
    monkeypatch.setattr(security_module, "decode_access_token", lambda _token, _config: payload)

    response = client.get("/page/admin-only", headers={"Authorization": "Bearer valid"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_role_required_allows_admin_for_html_route(client, monkeypatch):
    payload = {"sub": "admin-1", "username": "admin", "role": "admin"}
    monkeypatch.setattr(security_module, "decode_access_token", lambda _token, _config: payload)

    response = client.get("/page/admin-only", headers={"Authorization": "Bearer valid"})
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
