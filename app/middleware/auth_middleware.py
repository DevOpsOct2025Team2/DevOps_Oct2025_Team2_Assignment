from functools import wraps
from flask import request, jsonify, current_app, g
import jwt
from supabase import create_client
from datetime import datetime, timezone

import logging

# Setup logging
logger = logging.getLogger('auth_middleware')
logger.setLevel(logging.DEBUG)

# file logging in debug mode to prevent leaking secrets in production
if current_app.config.get("DEBUG") or current_app.config.get("AUTH_MIDDLEWARE_DEBUG"):
    handler = logging.FileHandler('middleware_debug.log')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = None
            # auth header
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ', 1)[1].strip()

            # fallback to HttpOnly cookie set by login()
            if not token:
                cookie_name = current_app.config.get("AUTH_COOKIE_NAME", "access_token")
                token = request.cookies.get(cookie_name)

            if not token:
                logger.error("Token is missing")
                return jsonify({'message': 'Token is missing'}), 401            
            try:
                jwt_secret = current_app.config.get('JWT_SECRET_KEY')
                if jwt_secret:
                    try:
                        # Supabase JWTs are HS256 by default
                        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"], options={"verify_aud": False})
                    except jwt.DecodeError as decode_err:
                        logger.warning("JWT decode error")
                        return jsonify({'message': 'Invalid token'}), 401
                    
                    user_id = payload.get('sub') or payload.get('user_id') or payload.get('id')
                    user_role = (payload.get('role') or payload.get('app_metadata', {}).get('role') or '').lower()
                    username = payload.get('username') or payload.get('email')
                    
                    # user attached to flask.g for downstream use
                    g.current_user = {
                        'id': user_id,
                        'username': username,
                        'role': user_role
                    }
                    
                    if required_role and user_role != required_role.lower():
                        logger.warning("Authorization failed: insufficient permissions")
                        return jsonify({'message': 'Insufficient permissions'}), 403
                        
                else:
                    # fallback to Supabase API if no local secret
                    supabase_url = current_app.config.get('SUPABASE_URL')
                    supabase_key = current_app.config.get('SUPABASE_KEY')
                    supabase = create_client(supabase_url, supabase_key)
                    
                    user_resp = supabase.auth.get_user(token)
                    if not user_resp:
                         logger.error("Supabase get_user failed")
                         return jsonify({'message': 'Invalid token'}), 401
                    
                    # extract user data
                    user_data = getattr(user_resp, 'data', None) or {}
                    u = user_data.get('user') if isinstance(user_data, dict) else user_data
                    
                    if not u:
                        logger.warning("Supabase user lookup returned empty")
                        return jsonify({'message': 'Invalid token'}), 401
                    
                    user_id = getattr(u, 'id', None) or getattr(u, 'uuid', None)
                    user_role = (getattr(u, 'role', None) or getattr(u, 'user_metadata', {}).get('role') or '').lower()
                    username = getattr(u, 'email', None)
                    
                    g.current_user = {
                        'id': user_id,
                        'username': username,
                        'role': user_role
                    }
                    
                    if required_role and user_role != required_role.lower():
                        logger.warning("Authorization failed: insufficient permissions")
                        return jsonify({'message': 'Insufficient permissions'}), 403
            
            except jwt.ExpiredSignatureError:
                logger.info("Token expiration detected")
                return jsonify({'message': 'Token has expired', 'detail': 'Session timed out. Please log in again.'}), 401
            except jwt.InvalidTokenError:
                logger.warning("Invalid token format")
                return jsonify({'message': 'Invalid token'}), 401
            except Exception as e:
                logger.exception("Unexpected authentication error")
                return jsonify({'message': 'Authentication error'}), 401

            return f(*args, **kwargs)
        return decorated_function
    return decorator
