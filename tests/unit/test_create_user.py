import pytest
from app import create_app
from app.services import auth_service
import uuid

@pytest.fixture
def app():
    app = create_app('testing')
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def admin_token(app):
    admin_user = {
        'id': 'admin-test-id',
        'username': 'admin_test',
        'role': 'admin'
    }
    return auth_service.create_access_token(admin_user, app.config)

@pytest.fixture
def valid_user_data():
    # unique username to avoid conflicts
    unique_username = f'testuser_{uuid.uuid4().hex[:8]}'
    return {
        'username': unique_username,
        'password': 'Password123',
        'role': 'regular'
    }

def test_create_user_success(client, admin_token, valid_user_data):
    response = client.post(
        '/api/v1/users',
        json=valid_user_data,
        headers={'Authorization': f'Bearer {admin_token}'}
    )
    assert response.status_code == 201
    assert 'User created successfully' in response.get_json()['message']

def test_create_user_username_too_short(client, admin_token):
    response = client.post(
        '/api/v1/users',
        json={'username': 'ab', 'password': 'Password123', 'role': 'regular'},
        headers={'Authorization': f'Bearer {admin_token}'}
    )
    assert response.status_code == 400
    assert 'Username must be 3-32 characters' in response.get_json()['error']

def test_create_user_password_too_short(client, admin_token):
    response = client.post(
        '/api/v1/users',
        json={'username': f'testuser_{uuid.uuid4().hex[:8]}', 'password': 'Pass1', 'role': 'regular'},
        headers={'Authorization': f'Bearer {admin_token}'}
    )
    assert response.status_code == 400
    assert 'Password must be at least 8 characters' in response.get_json()['error']

def test_create_user_invalid_role(client, admin_token):
    response = client.post(
        '/api/v1/users',
        json={'username': f'testuser_{uuid.uuid4().hex[:8]}', 'password': 'Password123', 'role': 'superadmin'},
        headers={'Authorization': f'Bearer {admin_token}'}
    )
    assert response.status_code == 400
    assert 'Invalid role' in response.get_json()['error']

def test_create_user_non_admin_forbidden(client, app):
    # Create a token for regular user
    regular_user = {
        'id': 'regular-user-id',
        'username': 'regular_user',
        'role': 'regular'
    }
    regular_token = auth_service.create_access_token(regular_user, app.config)
    
    response = client.post(
        '/api/v1/users',
        json={'username': f'newuser_{uuid.uuid4().hex[:8]}', 'password': 'Password123', 'role': 'regular'},
        headers={'Authorization': f'Bearer {regular_token}'}
    )
    assert response.status_code == 403
    assert 'Unauthorized' in response.get_json()['error']

def test_create_user_missing_auth_token(client, valid_user_data):
    # test w/o token
    response = client.post('/api/v1/users', json=valid_user_data)
    assert response.status_code == 401