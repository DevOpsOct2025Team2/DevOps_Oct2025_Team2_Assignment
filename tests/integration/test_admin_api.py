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
    """Generate JWT token with user_id for consistent testing"""
    payload = {
        'sub': user_id,
        'role': role,
        'app_metadata': {'role': role},
        'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, secret, algorithm='HS256')

class TestAdminAccess:
    def test_no_token(self, client):
        """Unauthenticated request returns 401"""
        response = client.get('/api/v1/admin/users')
        assert response.status_code == 401

    def test_bad_token(self, client):
        """Malformed token returns 401"""
        response = client.get('/api/v1/admin/users', headers={
            'Authorization': 'Bearer invalidtoken'
        })
        assert response.status_code == 401

    def test_expired_token(self, client):
        """Expired token returns 401"""
        payload = {
            'sub': 'test-admin',
            'role': 'admin',
            'exp': datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=1),
        }
        token = jwt.encode(payload, 'test-secret', algorithm='HS256')

        response = client.get('/api/v1/admin/users', headers={
            'Authorization': f'Bearer {token}'
        })
        assert response.status_code == 401

    def test_unauthorized_role(self, client):
        """Non-admin role returns 403"""
        token = generate_token('regular', user_id='test-user')
        response = client.get('/api/v1/admin/users', headers={
            'Authorization': f'Bearer {token}'
        })
        assert response.status_code == 403

    @patch('app.routes.api.UserService')
    def test_authorized_role(self, MockService, client):
        """Admin role can access endpoint"""
        token = generate_token('admin', user_id='test-admin')

        mock_instance = MockService.return_value
        mock_instance.get_all_users.return_value = {
            'users': [],
            'page': 1,
            'per_page': 10,
            'total': 0,
        }

        response = client.get('/api/v1/admin/users', headers={
            'Authorization': f'Bearer {token}'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'users' in data