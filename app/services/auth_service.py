from datetime import datetime, timedelta, timezone
import logging

import bcrypt
import jwt

from app.services.supabase_client import get_supabase_client
logger = logging.getLogger(__name__)


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, password_hash):
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def get_user_by_username(username, supabase_client=None):
    try:
        client = supabase_client or get_supabase_client()
        response = (
            client.table("users")
            .select("id, username, password_hash, role, is_active")
            .eq("username", username)
            .single()
            .execute()
        )
        if response.data:
            return response.data
    except Exception as e:
        logger.debug(f"User lookup error for {username}: {str(e)}")
        return None
    return None


def authenticate_user(username, password, supabase_client=None):
    user = get_user_by_username(username, supabase_client=supabase_client)
    if not user:
        return None
    if user.get("is_active") is False:
        return None

    if not verify_password(password, user.get("password_hash", "")):
        return None

    role = (user.get("role") or "").strip().lower()
    user["role"] = role
    return user


def create_access_token(user, config):
    expires_in = int(config.get("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "role": user["role"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    return jwt.encode(payload, config["JWT_SECRET_KEY"], algorithm="HS256")


def decode_access_token(token, config):
    try:
        return jwt.decode(token, config["JWT_SECRET_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise
