import os
from supabase import create_client, Client
from flask import current_app
import logging
import logging

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        self.url: str = current_app.config.get('SUPABASE_URL')
        self.key: str = current_app.config.get('SUPABASE_SERVICE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("Supabase credentials not configured")
            
        self.supabase: Client = create_client(self.url, self.key)

    def get_all_users(self, page=1, per_page=10, search_query=None, sort_by='created_at', sort_order='desc'):
        """
        Fetch all users from 'users' table with pagination, search, and sorting.
        """
        try:
            # 1. Build Query
            query = self.supabase.table('users').select('*', count='exact')
            
            # 2. Search
            if search_query:
                # ilike for case-insensitive search on username
                query = query.ilike('username', f'%{search_query}%')
            
            # 3. Sorting
            # e.g., sort_by='created_at', sort_order='desc'
            if sort_by:
                query = query.order(sort_by, desc=(sort_order == 'desc'))
            
            # 4. Pagination
            start = (page - 1) * per_page
            end = start + per_page - 1
            query = query.range(start, end)
            
            # 5. Execute
            response = query.execute()
            
            # 6. Transform
            users = []
            if response.data:
                for user in response.data:
                    users.append({
                        'id': user.get('id'),
                        'username': user.get('username'), # In public table usually username, not email
                        'email': user.get('email', ''),   # Might not be in public table? Check schema assumptions.
                                                          # Based on auth_service, we select: id, username, password_hash, role, is_active
                        'role': user.get('role'),
                        'created_at': user.get('created_at'),
                        # 'last_sign_in_at': ... # Might not exist in public table unless synced
                        'is_active': user.get('is_active')
                    })
            
            return {
                'users': users,
                'page': page,
                'per_page': per_page,
            # Log error with stack trace on the server, but do not expose details to the client
            logging.exception("Error fetching users")
            return {'users': [], 'error': 'Failed to fetch users'}
            # Log full error with stack trace on the server, but do not expose details to the client
            logger.exception("Error fetching users")
            return {'users': [], 'error': 'Failed to fetch users'}

    def get_user_by_id(self, user_id):
        try:
            user = self.supabase.auth.admin.get_user_by_id(user_id)
            return user
        except Exception as e:
            return None
