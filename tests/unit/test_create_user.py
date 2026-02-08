import pytest
import jwt
import datetime
from datetime import timezone
from unittest.mock import patch, MagicMock
from app import create_app

@pytest.fixture
def client():
    app = create_app('testing')
    app.config['JWT_SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client

def generate_token(role, secret='test-secret', user_id='test-admin'):
    payload = {
        'sub': user_id,
        'role': role,
        'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, secret, algorithm='HS256')

def test_create_user_missing_auth_token(client):
    """Test missing authorization token returns 401"""
    response = client.post('/api/v1/auth/users', json={
        'username': 'newuser',
        'password': 'TestPass123!',
        'role': 'regular'
    })
    assert response.status_code == 401

def test_create_user_non_admin_forbidden(client):
    """Test non-admin user cannot create users"""
    token = generate_token('regular', user_id='regular-user')
    response = client.post('/api/v1/auth/users', 
        json={
            'username': 'newuser',
            'password': 'TestPass123!',
            'role': 'regular'
        },
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 403

def test_create_user_username_too_short(client):
    """Test username must be at least 3 characters"""
    token = generate_token('admin', user_id='admin-user')
    response = client.post('/api/v1/auth/users',
        json={
            'username': 'ab',
            'password': 'TestPass123!',
            'role': 'regular'
        },
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 400
    assert 'Username' in response.get_json().get('error', '')

def test_create_user_password_too_short(client):
    """Test password must be at least 8 characters"""
    token = generate_token('admin', user_id='admin-user')
    response = client.post('/api/v1/auth/users',
        json={
            'username': 'newuser',
            'password': 'short',
            'role': 'regular'
        },
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 400
    assert 'Password' in response.get_json().get('error', '')

def test_create_user_invalid_role(client):
    """Test invalid role is rejected"""
    token = generate_token('admin', user_id='admin-user')
    response = client.post('/api/v1/auth/users',
        json={
            'username': 'newuser',
            'password': 'TestPass123!',
            'role': 'superadmin'
        },
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 400
    assert 'role' in response.get_json().get('error', '').lower()

@patch('app.routes.api.auth_service')
@patch('app.routes.api.UserService')
def test_create_user_success(MockUserService, mock_auth_service, client):
    token = generate_token('admin', user_id='admin-user')

    mock_auth_service.hash_password = MagicMock(
        return_value='hashed_password_123'
    )

    mock_service_instance = MagicMock()
    MockUserService.return_value = mock_service_instance

    mock_service_instance.create_user.return_value = {
        'id': 'new-user-1',
        'username': 'newuser',
        'role': 'regular'
    }
    
    response = client.post('/api/v1/auth/users',
        json={
            'username': 'newuser',
            'password': 'TestPass123!',
            'role': 'regular'
        },
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == 'User created successfully.'