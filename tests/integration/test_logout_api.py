
from app.services import auth_service

def test_logout_success_clears_cookie_and_session(client, monkeypatch):
    def fake_authenticate_user(username, password, supabase_client=None):
        if username == "alice" and password == "secret":
            return {"id": "user-1", "username": "alice", "role": "admin"}
        return None

    monkeypatch.setattr(auth_service, "authenticate_user", fake_authenticate_user)

    # obtain access token cookie
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "secret"},
    )
    assert login_response.status_code == 200
    cookies = login_response.headers.get("Set-Cookie", "")
    assert "access_token=" in cookies

    # cookie used to call logout
    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Cookie": cookies},
    )
    assert logout_response.status_code == 200
    data = logout_response.get_json()
    assert data["success"] is True
    assert "logged out" in data["message"].lower()
    logout_cookies = logout_response.headers.get("Set-Cookie", "")
    assert "access_token=;" in logout_cookies


def test_logout_failure_unauthenticated(client):
    # logging out w/o cookie
    logout_response = client.post("/api/v1/auth/logout")
    # return unauthorized 
    assert logout_response.status_code in (401, 403)
    data = logout_response.get_json()
    assert data is not None
    assert "error" in data or "message" in data