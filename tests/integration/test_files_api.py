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

def generate_token(role, secret='test-secret', user_id='test-user'):
    payload = {
        'sub': user_id,
        'role': role,
        'app_metadata': {'role': role},
        'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, secret, algorithm='HS256')

class TestGetUserFiles:
    def test_no_token(self, client):
        """Unauthentication returns 401"""
        response = client.get('/api/v1/files/me')
        assert response.status_code == 401

    def test_admin_forbidden(self, client):
        """Admin users cannot access user files endpoint"""
        token = generate_token('admin', user_id='admin123')
        response = client.get('/api/v1/files/me', headers={
            'Authorization': f'Bearer {token}'
        })
        assert response.status_code == 403

    def test_expired_token(self, client):
        """Expired token returns 401"""
        payload = {
            'sub': 'user123',
            'role': 'regular',
            'exp': datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=1),
        }
        token = jwt.encode(payload, 'test-secret', algorithm='HS256')
        response = client.get('/api/v1/files/me', headers={
            'Authorization': f'Bearer {token}'
        })
        assert response.status_code == 401

    @patch('app.security.jwt.decode')
    @patch('app.routes.api.FileService')
    @patch('app.routes.api.auth_service.get_supabase_client')
    def test_success(self, mock_get_client, MockFileService, mock_jwt_decode, client):
        """Regular user retrieves own files"""
        token = generate_token('regular', user_id='user123')
        mock_result = {
            'files': [{
                'id': 'file1',
                'filename': 'document.pdf',
                'file_size': 2048,
                'file_type': 'application/pdf',
                'created_at': '2024-01-01T00:00:00Z',
            }],
            'page': 1,
            'per_page': 10,
            'total': 1,
        }

        mock_jwt_decode.return_value = {
            'sub': 'user123',
            'id': 'user123',
            'role': 'regular',
            'username': 'testuser'
        }
        mock_get_client.return_value = MagicMock()
        MockFileService.return_value.get_user_files.return_value = mock_result

        response = client.get('/api/v1/files/me', headers={
            'Authorization': f'Bearer {token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['files']) == 1
        assert data['files'][0]['filename'] == 'document.pdf'

class TestDeleteFile:
    def test_no_token(self, client):
        """Unauthentication returns 401"""
        response = client.delete('/api/v1/files/file1')
        assert response.status_code == 401

    @patch('app.security.jwt.decode')
    def test_admin_forbidden(self, mock_jwt_decode, client):
        """Admin users cannot delete via /files endpoint"""
        token = generate_token('admin', user_id='admin123')
        mock_jwt_decode.return_value = {
            'sub': 'admin123',
            'id': 'admin123',
            'role': 'admin',
            'username': 'adminuser'
        }
        response = client.delete('/api/v1/files/file1', headers={
            'Authorization': f'Bearer {token}'
        })
        assert response.status_code == 403

    @patch('app.security.jwt.decode')
    @patch('app.routes.api.FileService')
    @patch('app.routes.api.get_supabase_client')
    def test_unauthorized_owner(self, mock_get_client, MockFileService, mock_jwt_decode, client):
        """User cannot delete file they don't own"""
        token = generate_token('regular', user_id='user123')

        mock_jwt_decode.return_value = {
            'sub': 'user123',
            'id': 'user123',
            'role': 'regular',
            'username': 'testuser'
        }
        mock_get_client.return_value = MagicMock()
        MockFileService.return_value.delete_file.return_value = {
            'error': 'Unauthorized'
        }

        response = client.delete('/api/v1/files/other_users_file', headers={
            'Authorization': f'Bearer {token}'
        })

        assert response.status_code == 403

    @patch('app.security.jwt.decode')
    @patch('app.routes.api.FileService')
    @patch('app.routes.api.get_supabase_client')
    def test_success(self, mock_get_client, MockFileService, mock_jwt_decode, client):
        """Owner can delete their own file"""
        token = generate_token('regular', user_id='user123')

        mock_jwt_decode.return_value = {
            'sub': 'user123',
            'id': 'user123',
            'role': 'regular',
            'username': 'testuser'
        }
        mock_get_client.return_value = MagicMock()
        MockFileService.return_value.delete_file.return_value = {
            'success': True,
            'message': 'File deleted successfully'
        }

        response = client.delete('/api/v1/files/file1', headers={
            'Authorization': f'Bearer {token}'
        })

        assert response.status_code == 200
        assert 'successfully' in response.get_json()['message'].lower()