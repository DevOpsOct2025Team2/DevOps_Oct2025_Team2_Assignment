import app.services.auth_service as auth_service


def test_login_success_sets_cookie_and_redirect(client, monkeypatch):
    def fake_authenticate_user(username, password, supabase_client=None):
        if username == "alice" and password == "secret":
            return {"id": "user-1", "username": "alice", "role": "admin"}
        return None

    monkeypatch.setattr(auth_service, "authenticate_user", fake_authenticate_user)

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "secret"},
    )

    assert response.status_code == 200
    assert response.json["redirect_to"] == "/admin"
    assert "access_token=" in response.headers.get("Set-Cookie", "")


def test_login_failure_returns_unauthorized(client, monkeypatch):
    monkeypatch.setattr(auth_service, "authenticate_user", lambda *_args, **_kwargs: None)

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "wrong"},
    )

    assert response.status_code == 401
