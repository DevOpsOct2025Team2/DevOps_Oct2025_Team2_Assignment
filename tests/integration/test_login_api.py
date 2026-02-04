from dotenv import load_dotenv
load_dotenv()

import os
import app.services.auth_service as auth_service

# set default env vars for testing
TEST_USERNAME = os.environ.get("TEST_USERNAME")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD")

if not TEST_USERNAME or not TEST_PASSWORD:
    raise RuntimeError("TEST_USERNAME and TEST_PASSWORD must be set in .env")

def test_login_success_sets_cookie_and_redirect(client, monkeypatch):
    def fake_authenticate_user(username, password, supabase_client=None):
        if username == TEST_USERNAME and password == TEST_PASSWORD:
            return {"id": "user-1", "username": TEST_USERNAME, "role": "admin"}
        return None

    monkeypatch.setattr(auth_service, "authenticate_user", fake_authenticate_user)

    response = client.post(
        "/api/v1/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json["redirect_to"] == "/admin"
    assert "access_token=" in response.headers.get("Set-Cookie", "")


def test_login_failure_returns_unauthorized(client, monkeypatch):
    monkeypatch.setattr(auth_service, "authenticate_user", lambda *_args, **_kwargs: None)

    wrong_password = f"{TEST_PASSWORD}_wrong"

    response = client.post(
        "/api/v1/auth/login",
        json={"username": TEST_USERNAME, "password": wrong_password},
    )

    assert response.status_code == 401
