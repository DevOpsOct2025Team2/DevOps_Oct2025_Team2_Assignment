from unittest.mock import MagicMock, patch

import pytest

from app.services.user_service import UserService


@pytest.fixture
def mock_supabase():
    with patch("app.services.user_service.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        yield mock_client


@pytest.fixture
def app_context():
    from app import create_app

    app = create_app("testing")
    app.config["SUPABASE_URL"] = "http://test-supabase-url.com"
    app.config["SUPABASE_SERVICE_KEY"] = "test-service-key"
    with app.app_context():
        yield app


def test_get_all_users_success(mock_supabase, app_context):
    """Test successful user retrieval"""
    mock_data = [
        {
            "id": "user1",
            "username": "test_user",
            "email": "test1@example.com",
            "role": "authenticated",
            "created_at": "2024-01-01T00:00:00Z",
            "is_active": True,
        }
    ]

    mock_query = MagicMock()
    mock_query.ilike.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query

    mock_response = MagicMock()
    mock_response.data = mock_data
    mock_response.count = 1
    mock_query.execute.return_value = mock_response

    mock_supabase.table.return_value.select.return_value = mock_query

    service = UserService()
    result = service.get_all_users(page=1, per_page=10)

    assert len(result["users"]) == 1
    assert result["users"][0]["username"] == "test_user"
    assert result["page"] == 1
    assert result["total"] == 1


def test_get_all_users_error(mock_supabase, app_context):
    # Mock chain to raise exception
    mock_supabase.table.return_value.select.side_effect = Exception("Supabase error")

    service = UserService()
    result = service.get_all_users()

    assert "error" in result
    assert result["error"] == "Supabase error"
    assert result["users"] == []


def test_get_all_users_invalid_pagination(mock_supabase, app_context):
    """Test invalid pagination parameters"""
    service = UserService()

    # page < 1
    result = service.get_all_users(page=0)
    assert "error" in result
    assert result["error"] == "Invalid pagination parameters"

    # per_page > 100
    result = service.get_all_users(per_page=150)
    assert "error" in result
    assert result["error"] == "Invalid pagination parameters"


def test_get_all_users_sort_validation(mock_supabase, app_context):
    """Test invalid sort field defaults to created_at"""
    mock_query = MagicMock()
    mock_query.ilike.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query

    mock_response = MagicMock()
    mock_response.data = []
    mock_response.count = 0
    mock_query.execute.return_value = mock_response

    mock_supabase.table.return_value.select.return_value = mock_query

    service = UserService()
    result = service.get_all_users(sort_by="invalid_field")

    assert "users" in result
    mock_query.order.assert_called()


def test_get_user_by_id_success(mock_supabase, app_context):
    """Test successful user retrieval by ID"""
    mock_user = {"id": "user1", "username": "test_user", "email": "test@example.com"}

    mock_supabase.auth.admin.get_user_by_id.return_value = mock_user

    service = UserService()
    result = service.get_user_by_id("user1")

    assert result == mock_user


def test_get_user_by_id_invalid_input(mock_supabase, app_context):
    """Test invalid user_id returns None"""
    service = UserService()

    # test None
    assert service.get_user_by_id(None) is None
    # test empty string
    assert service.get_user_by_id("") is None
    # test non-string
    assert service.get_user_by_id(123) is None


def test_get_user_by_id_error(mock_supabase, app_context):
    """Test error handling returns None"""
    mock_supabase.auth.admin.get_user_by_id.side_effect = Exception("Auth error")

    service = UserService()
    result = service.get_user_by_id("user1")

    assert result is None
