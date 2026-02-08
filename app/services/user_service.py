import logging

from flask import current_app
from supabase import Client, create_client

logger = logging.getLogger(__name__)


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
        try:
            page = max(int(page), 1)
            per_page = max(int(per_page), 1)

            query = self.supabase.table("users").select("*", count="exact")

            if search_query:
                query = query.ilike("username", f"%{search_query}%")

            if sort_by:
                query = query.order(sort_by, desc=(sort_order == "desc"))

            start = (page - 1) * per_page
            end = start + per_page - 1
            response = query.range(start, end).execute()

            users = []
            if response.data:
                for user in response.data:
                    users.append(
                        {
                            "id": user.get("id"),
                            "username": user.get("username"),
                            "email": user.get("email", ""),
                            "role": user.get("role"),
                            "created_at": user.get("created_at"),
                            "is_active": user.get("is_active"),
                        }
                    )

            total = response.count if response.count is not None else len(users)
            return {
                "users": users,
                "page": page,
                "per_page": per_page,
                "total": total,
            }

        except Exception as exc:
            logger.exception("Error fetching users")
            return {
                "users": [],
                "page": page,
                "per_page": per_page,
                "total": 0,
                "error": str(exc) if current_app and current_app.config.get("TESTING") else "Failed to fetch users",
            }

    def get_user_by_id(self, user_id):
        try:
            response = (
                self.supabase.table("users")
                .select("id, username, role, is_active")
                .eq("id", user_id)
                .limit(1)
                .execute()
            )
            if response.data:
                return response.data[0]
            return None
        except Exception:
            logger.exception("Error fetching user by id")
            return None

    def delete_user_by_id(self, user_id):
        try:
            response = self.supabase.table("users").delete().eq("id", user_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception:
            logger.exception("Error deleting user by id")
            return None