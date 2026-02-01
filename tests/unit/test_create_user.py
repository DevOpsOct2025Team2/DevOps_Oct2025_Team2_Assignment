import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app('testing')
    client = app.test_client()
    
    with app.app_context():
        # simulation of login as admin user
        with client.session_transaction() as sess:
            sess['user_id'] = 'admin_test_id'
        yield client

@pytest.fixture
def valid_user_data():
    return {
        'username': 'testuser',
        'password': 'Password123',
        'role': 'user'
    }

@pytest.fixture
def valid_admin_session(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 'admin_test_id'
    return client

def test_create_user_success(client, valid_user_data):
    response = client.post('/api/v1/users', json=valid_user_data)
    assert response.status_code == 201
    assert 'User created successfully' in response.get_json()['message']

def test_create_user_username_too_short(client):
    response = client.post('/api/v1/users', json={
        'username': 'ab',
        'password': 'Password123',
        'role': 'user'
    })
    assert response.status_code == 400
    assert 'Username must be 3-32 characters' in response.get_json()['error']

def test_create_user_password_too_short(client):
    response = client.post('/api/v1/users', json={
        'username': 'testuser',
        'password': 'Pass1',
        'role': 'user'
    })
    assert response.status_code == 400
    assert 'Password must be at least 8 characters' in response.get_json()['error']

def test_create_user_invalid_role(client):
    response = client.post('/api/v1/users', json={
        'username': 'testuser',
        'password': 'Password123',
        'role': 'superadmin'
    })
    assert response.status_code == 400
    assert 'Invalid role' in response.get_json()['error']

def test_create_user_non_admin_forbidden(client):
    # simulation of regular user login
    with client.session_transaction() as sess:
        sess['user_id'] = 'regular_user_id'
    
    response = client.post('/api/v1/users', json={
        'username': 'newuser',
        'password': 'Password123',
        'role': 'user'
    })
    assert response.status_code == 403
    assert 'Unauthorized' in response.get_json()['error']