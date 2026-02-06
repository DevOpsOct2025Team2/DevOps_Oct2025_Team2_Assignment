import pytest
from unittest.mock import MagicMock, patch
from app.services.user_service import UserService

@pytest.fixture
def mock_supabase():
    with patch('app.services.user_service.create_client') as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        yield mock_client

@pytest.fixture
def app_context():
    from app import create_app
    app = create_app('testing')
    app.config['SUPABASE_URL'] = 'http://test-supabase-url.com'
    app.config['SUPABASE_SERVICE_KEY'] = 'test-service-key'
    with app.app_context():
        yield app

def test_get_all_users_success(mock_supabase, app_context):
    # Mock data structure matching Supabase generic response
    mock_data = [{
        "id": "user1",
        "username": "test_user",
        "email": "test1@example.com",
        "role": "authenticated",
        "created_at": "2024-01-01T00:00:00Z",
        "is_active": True
    }]
    
    # Mock chain: table('users').select(...).ilike(...).order(...).range(...).execute()
    # Simplified: just ensure execute returns the data
    mock_query = MagicMock()
    mock_query.ilike.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = mock_data
    mock_response.count = 1
    mock_query.execute.return_value = mock_response
    
    # Setup chain
    mock_supabase.table.return_value.select.return_value = mock_query
    
    service = UserService()
    result = service.get_all_users(page=1, per_page=10)
    
    assert len(result['users']) == 1
    assert result['users'][0]['username'] == "test_user"
    assert result['page'] == 1
    assert result['total'] == 1

def test_get_all_users_error(mock_supabase, app_context):
    # Mock chain to raise exception
    mock_supabase.table.return_value.select.side_effect = Exception("Supabase error")
    
    service = UserService()
    result = service.get_all_users()
    
    assert 'error' in result
    assert result['error'] == "Supabase error"


def test_get_user_by_id_success(mock_supabase, app_context):
    mock_response = MagicMock()
    mock_response.data = [{"id": "user-1", "username": "alice", "role": "regular", "is_active": True}]
    (
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute
        .return_value
    ) = mock_response

    service = UserService()
    result = service.get_user_by_id("user-1")

    assert result is not None
    assert result["id"] == "user-1"
    assert result["username"] == "alice"


def test_get_user_by_id_not_found(mock_supabase, app_context):
    mock_response = MagicMock()
    mock_response.data = []
    (
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute
        .return_value
    ) = mock_response

    service = UserService()
    result = service.get_user_by_id("missing-user")

    assert result is None


def test_delete_user_by_id_success(mock_supabase, app_context):
    mock_response = MagicMock()
    mock_response.data = [{"id": "user-2", "username": "bob"}]
    mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response

    service = UserService()
    result = service.delete_user_by_id("user-2")

    assert result is not None
    assert result["id"] == "user-2"


def test_delete_user_by_id_error(mock_supabase, app_context):
    mock_supabase.table.return_value.delete.side_effect = Exception("Delete failed")

    service = UserService()
    result = service.delete_user_by_id("user-3")

    assert result is None
