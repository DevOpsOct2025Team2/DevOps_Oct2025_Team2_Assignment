import pytest
import jwt
import datetime
from app import create_app

@pytest.fixture
def client():
    app = create_app('testing')
    app.config['JWT_SECRET_KEY'] = 'test-secret'
    with app.test_client() as client:
        yield client

def generate_token(role, secret='test-secret'):
    payload = {
        'role': role,
        'app_metadata': {'role': role},
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, secret, algorithm='HS256')

def test_admin_access_no_token(client):
    response = client.get('/api/v1/admin/users')
    assert response.status_code == 401

def test_admin_access_bad_token(client):
    response = client.get('/api/v1/admin/users', headers={
        'Authorization': 'Bearer invalidtoken'
    })
    assert response.status_code == 401


def test_admin_access_unauthorized_role(client):
    token = generate_token('authenticated')
    response = client.get('/api/v1/admin/users', headers={
        'Authorization': f'Bearer {token}'
    })
    # The middleware now checks for 'admin' role
    assert response.status_code == 403

from unittest.mock import patch

def test_admin_access_authorized_role(client):
    token = generate_token('admin')
    
    # We also need to mock UserService.get_all_users so it doesn't fail trying to connect to real Supabase
    with patch('app.routes.api.UserService') as MockService:
        mock_instance = MockService.return_value
        mock_instance.get_all_users.return_value = {'users': [], 'page': 1, 'per_page': 10, 'total': 0}
        
        response = client.get('/api/v1/admin/users', headers={
            'Authorization': f'Bearer {token}'
        })
        assert response.status_code == 200
