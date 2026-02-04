from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class StubResponse:
    def __init__(self, data=None):
        self.data = data
        self.error = None


class StubTable:
    def __init__(self, data):
        self._data = data
        self._value = None

    def select(self, _fields):
        return self

    def eq(self, _field, value):
        self._value = value
        return self

    def single(self):
        return self

    def execute(self):
        if self._data and self._data.get("username") == self._value:
            return StubResponse(self._data)
        return StubResponse(None)

class StubClient:
    def __init__(self, data):
        self._data = data

    def table(self, _name):
        return StubTable(self._data)


def test_hash_and_verify_password():
    hashed = hash_password("secret-pass")
    assert isinstance(hashed, str)
    assert verify_password("secret-pass", hashed)
    assert not verify_password("wrong-pass", hashed)


def test_authenticate_user_success():
    user = {
        "id": "user-1",
        "username": "alice",
        "password_hash": hash_password("secret"),
        "role": "Admin",
        "is_active": True,
    }
    client = StubClient(user)
    result = authenticate_user("alice", "secret", supabase_client=client)
    assert result is not None
    assert result["role"] == "admin"


def test_authenticate_user_wrong_password():
    user = {
        "id": "user-2",
        "username": "bob",
        "password_hash": hash_password("secret"),
        "role": "regular",
        "is_active": True,
    }
    client = StubClient(user)
    result = authenticate_user("bob", "not-secret", supabase_client=client)
    assert result is None


def test_create_and_decode_access_token():
    user = {"id": "user-3", "username": "carol", "role": "regular"}
    config = {"JWT_SECRET_KEY": "test-secret", "JWT_ACCESS_TOKEN_EXPIRES": 60}
    token = create_access_token(user, config)
    decoded = decode_access_token(token, config)
    assert decoded["sub"] == "user-3"
    assert decoded["username"] == "carol"
    assert decoded["role"] == "regular"
