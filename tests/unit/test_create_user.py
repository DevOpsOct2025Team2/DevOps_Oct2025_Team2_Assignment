import unittest
from app import create_app, db
from app.models import User
from werkzeug.security import check_password_hash

class TestCreateUser(unittest.TestCase):
  
   def setUp(self):
       self.app = create_app('testing')
       self.client = self.app.test_client()
       self.app_context = self.app.app_context()
       self.app_context.push()
       db.create_all()
      
       # create admin user for test
       admin = User(
           username='admin',
           password_hash='hashed_password',
           role='admin'
       )
       db.session.add(admin)
       db.session.commit()
      
       # login as admin
       with self.client.session_transaction() as sess:
           sess['user_id'] = admin.id
  
   def tearDown(self):
       db.session.remove()
       db.drop_all()
       self.app_context.pop()
  
   def test_create_user_success(self):
       response = self.client.post('/api/users', json={
           'username': 'testuser',
           'password': 'Password123',
           'role': 'user'
       })
      
       self.assertEqual(response.status_code, 201)
       self.assertIn('User created successfully', response.get_json()['message'])
      
       # verify if user exists in database
       user = User.query.filter_by(username='testuser').first()
       self.assertIsNotNone(user)
       self.assertEqual(user.role, 'user')
  
   def test_create_user_password_hashed(self):
       response = self.client.post('/api/users', json={
           'username': 'secureuser',
           'password': 'SecurePass99',
           'role': 'user'
       })
      
       self.assertEqual(response.status_code, 201)
      
       user = User.query.filter_by(username='secureuser').first()
       self.assertNotEqual(user.password_hash, 'SecurePass99')
       self.assertTrue(check_password_hash(user.password_hash, 'SecurePass99'))
  
   def test_create_user_username_too_short(self):
       response = self.client.post('/api/users', json={
           'username': 'ab',
           'password': 'Password123',
           'role': 'user'
       })
      
       self.assertEqual(response.status_code, 400)
       self.assertIn('Username must be 3-32 characters', response.get_json()['error'])
  
   def test_create_user_username_too_long(self):
       response = self.client.post('/api/users', json={
           'username': 'a' * 33,
           'password': 'Password123',
           'role': 'user'
       })
      
       self.assertEqual(response.status_code, 400)
       self.assertIn('Username must be 3-32 characters', response.get_json()['error'])
  
   def test_create_user_password_too_short(self):
       response = self.client.post('/api/users', json={
           'username': 'testuser',
           'password': 'Pass1',
           'role': 'user'
       })
      
       self.assertEqual(response.status_code, 400)
       self.assertIn('Password must be at least 8 characters', response.get_json()['error'])
  
   def test_create_user_password_no_letters(self):
       response = self.client.post('/api/users', json={
           'username': 'testuser',
           'password': '12345678',
           'role': 'user'
       })
      
       self.assertEqual(response.status_code, 400)
       self.assertIn('Password must be at least 8 characters with letters and numbers', response.get_json()['error'])
  
   def test_create_user_password_no_numbers(self):
       response = self.client.post('/api/users', json={
           'username': 'testuser',
           'password': 'PasswordOnly',
           'role': 'user'
       })
      
       self.assertEqual(response.status_code, 400)
       self.assertIn('Password must be at least 8 characters with letters and numbers', response.get_json()['error'])
  
   def test_create_user_invalid_role(self):
       response = self.client.post('/api/users', json={
           'username': 'testuser',
           'password': 'Password123',
           'role': 'superadmin'
       })
      
       self.assertEqual(response.status_code, 400)
       self.assertIn('Invalid role', response.get_json()['error'])
  
   def test_create_user_duplicate_username(self):
       # create first user
       self.client.post('/api/users', json={
           'username': 'duplicate',
           'password': 'Password123',
           'role': 'user'
       })
      
       # try to create second user with same username
       response = self.client.post('/api/users', json={
           'username': 'duplicate',
           'password': 'Password456',
           'role': 'user'
       })
      
       self.assertEqual(response.status_code, 409)
       self.assertIn('Username already exists', response.get_json()['error'])
  
   def test_create_user_non_admin_forbidden(self):
       # create regular user
       regular_user = User(
           username='regularuser',
           password_hash='hashed_password',
           role='user'
       )
       db.session.add(regular_user)
       db.session.commit()
      
       # login as regular user
       with self.client.session_transaction() as sess:
           sess['user_id'] = regular_user.id
      
       response = self.client.post('/api/users', json={
           'username': 'newuser',
           'password': 'Password123',
           'role': 'user'
       })
      
       self.assertEqual(response.status_code, 403)
       self.assertIn('Unauthorized', response.get_json()['error'])
  
   def test_create_admin_user(self):
       response = self.client.post('/api/users', json={
           'username': 'newadmin',
           'password': 'AdminPass123',
           'role': 'admin'
       })
      
       self.assertEqual(response.status_code, 201)
      
       user = User.query.filter_by(username='newadmin').first()
       self.assertEqual(user.role, 'admin')

if __name__ == '__main__':
   unittest.main()