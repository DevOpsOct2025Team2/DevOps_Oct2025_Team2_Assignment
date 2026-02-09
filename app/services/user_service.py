import logging

from flask import current_app
from supabase import Client, create_client

logger = logging.getLogger(__name__)
ALLOWED_SORT_FIELDS = {"created_at", "username", "role", "is_active"}


class UserService:
    def __init__(self):
        self.url: str = current_app.config.get("SUPABASE_URL")
        self.key: str = current_app.config.get("SUPABASE_SERVICE_KEY")

        if not self.url or not self.key:
            raise ValueError("Supabase credentials not configured")

        self.supabase: Client = create_client(self.url, self.key)

    def get_all_users(
        self,
        page=1,
        per_page=10,
        search_query=None,
        sort_by="created_at",
        sort_order="desc",
    ):
        """Fetch all users from 'users' table with pagination, search, and sorting by admins"""
        try:
            # Input validation
            if page < 1 or per_page < 1 or per_page > 100:
                return {"users": [], "error": "Invalid pagination parameters"}

            # Validate sort_by to prevent SQL injection
            if sort_by not in ALLOWED_SORT_FIELDS:
                sort_by = "created_at"

            if sort_order not in ("asc", "desc"):
                sort_order = "desc"

            # Build query
            query = self.supabase.table("users").select("*", count="exact")

            # Search using parameterized query - Supabase SDK
            if search_query and isinstance(search_query, str):
                search_query = search_query.strip()
                if search_query:
                    query = query.ilike("username", f"%{search_query}%")

            # Sorting
            query = query.order(sort_by, desc=(sort_order == "desc"))

            # Pagination
            start = (page - 1) * per_page
            end = start + per_page - 1
            query = query.range(start, end)

            # Execute
            response = query.execute()

            # Transform
            users = []
            if response.data:
                for user in response.data:
                    users.append(
                        {
                            "id": user.get("id"),
                            "username": user.get("username"),
                            "role": user.get("role"),
                            "created_at": user.get("created_at"),
                            "is_active": user.get("is_active"),
                        }
                    )

            return {
                "users": users,
                "page": page,
                "per_page": per_page,
                "total": response.count or 0,
            }
        except Exception as exc:
            logger.exception("Error fetching users")
            return {
                "users": [],
                "page": page,
                "per_page": per_page,
                "total": 0,
                "error": str(exc)
                if current_app and current_app.config.get("TESTING")
                else "Failed to fetch users",
            }

    def get_user_by_id(self, user_id):
        try:
            if not user_id or not isinstance(user_id, str):
                return None

            user = self.supabase.auth.admin.get_user_by_id(user_id)
            return user
        except Exception:
            logger.debug("User lookup failed")
            return None

    def create_user(self, username, password_hash, role):
        try:
            if not username or not isinstance(username, str):
                return {"error": "Invalid username"}
            if not password_hash or not isinstance(password_hash, str):
                return {"error": "Invalid password"}
            if role not in ("regular", "admin"):
                return {"error": "Invalid role"}

            response = (
                self.supabase.table("users")
                .insert(
                    {
                        "username": username,
                        "password_hash": password_hash,
                        "role": role,
                        "is_active": True,
                    }
                )
                .execute()
            )

            if response.data:
                return {
                    "id": response.data[0].get("id"),
                    "username": response.data[0].get("username"),
                    "role": response.data[0].get("role"),
                }
            return {"error": "Failed to create user"}
        except Exception:
            logger.exception("Error creating user")
            return {"error": "Failed to create user"}

    def delete_user_by_id(self, user_id):
        try:
            response = self.supabase.table("users").delete().eq("id", user_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception:
            logger.exception("Error deleting user by id")
            return None
