import pytest
import jwt
import datetime
from datetime import timezone
from unittest.mock import patch
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
        'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, secret, algorithm='HS256')

def test_logout_no_token(client):
    """Test logout without token returns 401"""
    response = client.post('/api/v1/auth/logout')
    assert response.status_code == 401

def test_logout_clears_session_and_cookies(client):
    token = generate_token('regular', user_id='user-1')
    
    response = client.post('/api/v1/auth/logout', headers={
        'Authorization': f'Bearer {token}'
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data.get('success') is True
    assert data.get('redirect_to') == '/login'
    
    assert 'Set-Cookie' in response.headers

def test_logout_invalid_token(client):
    """Test invalid token returns 401"""
    response = client.post('/api/v1/auth/logout', headers={
        'Authorization': 'Bearer invalidtoken'
    })
    assert response.status_code == 401

def test_logout_expired_token(client):
    """Test expired token returns 401"""
    payload = {
        'sub': 'user-1',
        'role': 'regular',
        'exp': datetime.datetime.now(timezone.utc) - datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, 'test-secret', algorithm='HS256')
    
    response = client.post('/api/v1/auth/logout', headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 401