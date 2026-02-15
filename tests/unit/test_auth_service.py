import datetime

import jwt
import pytest

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


@pytest.fixture
def jwt_config():
    """Standard JWT config for testing"""
    return {"JWT_SECRET_KEY": "test-secret", "JWT_ACCESS_TOKEN_EXPIRES": 60}


def test_hash_and_verify_password():
    """Password hashing and verification works correctly"""
    hashed = hash_password("secret-pass")
    assert isinstance(hashed, str)
    assert verify_password("secret-pass", hashed)
    assert not verify_password("wrong-pass", hashed)


def test_authenticate_user_success():
    """Valid credentials return authenticated user with normalized role"""
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
    """Wrong password returns None"""
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
    """JWT token round-trip preserves payload"""
    user = {"id": "user-3", "username": "carol", "role": "regular"}
    config = {"JWT_SECRET_KEY": "test-secret", "JWT_ACCESS_TOKEN_EXPIRES": 60}
    token = create_access_token(user, config)
    decoded = decode_access_token(token, config)
    assert decoded["sub"] == "user-3"
    assert decoded["username"] == "carol"
    assert decoded["role"] == "regular"


def test_authenticate_user_inactive_returns_none():
    """Inactive users cannot authenticate"""
    user = {
        "id": "user-4",
        "username": "dave",
        "password_hash": hash_password("secret"),
        "role": "regular",
        "is_active": False,
    }
    client = StubClient(user)
    result = authenticate_user("dave", "secret", supabase_client=client)
    assert result is None


def test_decode_access_token_invalid_signature_raises():
    """Tampered token with wrong signature raises InvalidTokenError"""
    token = jwt.encode(
        {
            "sub": "u1",
            "username": "eve",
            "role": "regular",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=10),
        },
        "wrong-secret",
        algorithm="HS256",
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, {"JWT_SECRET_KEY": "test-secret"})


def test_decode_access_token_expired_token_raises():
    """Expired token raises ExpiredSignatureError"""
    token = jwt.encode(
        {
            "sub": "u1",
            "username": "eve",
            "role": "regular",
            "exp": datetime.datetime.utcnow() - datetime.timedelta(minutes=1),
        },
        "test-secret",
        algorithm="HS256",
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token, {"JWT_SECRET_KEY": "test-secret"})

def test_authenticate_user_missing_password_returns_none():
    """Empty password rejected during authentication"""
    user = {
        "id": "user-5",
        "username": "alice",
        "password_hash": hash_password("secret"),
        "role": "regular",
        "is_active": True,
    }

    client = StubClient(user)
    result = authenticate_user("alice", "", supabase_client=client)

    assert result is None


def test_decode_access_token_missing_subject_raises():
    """Missing required 'sub' claim raises InvalidTokenError"""
    token = jwt.encode(
        {
            "username": "eve",
            "role": "regular",
            "exp": datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(minutes=10),
        },
        "test-secret",
        algorithm="HS256",
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, {"JWT_SECRET_KEY": "test-secret"})


@pytest.mark.parametrize("expires_offset_minutes", [1, 5, 60])
def test_create_access_token_with_various_expiration(jwt_config, expires_offset_minutes):
    """Token expiration times are correctly encoded"""
    user = {"id": "user-6", "username": "frank", "role": "admin"}
    config = jwt_config.copy()
    config["JWT_ACCESS_TOKEN_EXPIRES"] = expires_offset_minutes * 60
    
    token = create_access_token(user, config)
    decoded = decode_access_token(token, config)
    
    assert decoded["sub"] == "user-6"
    assert decoded["role"] == "admin"


@pytest.mark.parametrize(
    "user_state,expected",
    [
        ({"is_active": False, "password": "secret"}, None),  # Inactive user
        ({"is_active": True, "password": ""}, None),           # Empty password
        ({"is_active": True, "password": "wrong"}, None),      # Wrong password
    ],
)
def test_authenticate_user_failure_scenarios(user_state, expected):
    """Authentication fails for inactive users, empty/wrong passwords"""
    user = {
        "id": "user-test",
        "username": "testuser",
        "password_hash": hash_password("secret"),
        "role": "regular",
        "is_active": user_state["is_active"],
    }
    
    client = StubClient(user)
    result = authenticate_user("testuser", user_state["password"], supabase_client=client)
    
    assert result == expected

@pytest.mark.parametrize(
    "db_response,expected",
    [
        (None, None),  # user not found
        ({}, None),    # empty response
    ],
)
def test_authenticate_user_user_not_found(db_response, expected):
    """Authentication returns None when user does not exist"""
    client = StubClient(db_response)
    result = authenticate_user("unknown", "secret", supabase_client=client)
    assert result == expected


def test_decode_access_token_missing_sub_raises():
    """Missing required 'sub' claim raises InvalidTokenError"""
    token = jwt.encode(
        {
            "username": "eve",
            "exp": datetime.datetime.utcnow()
            + datetime.timedelta(minutes=10),
        },
        "test-secret",
        algorithm="HS256",
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(
            token,
            {"JWT_SECRET_KEY": "test-secret"},
        )


def test_decode_access_token_missing_username_allowed():
    """Token without username still decodes successfully"""
    token = jwt.encode(
        {
            "sub": "u1",
            "exp": datetime.datetime.utcnow()
            + datetime.timedelta(minutes=10),
        },
        "test-secret",
        algorithm="HS256",
    )

    decoded = decode_access_token(
        token,
        {"JWT_SECRET_KEY": "test-secret"},
    )

    assert isinstance(decoded, dict)
    assert decoded["sub"] == "u1"
