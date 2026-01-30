from functools import wraps
from flask import request, jsonify, current_app
import jwt
from supabase import create_client
from datetime import datetime, timezone

import logging
import sys

# Setup logging
handler = logging.FileHandler('middleware_debug.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger('auth_middleware')
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = None
            
            # Check for Authorization header
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                try:
                    token = auth_header.split(" ")[1]
                except IndexError:
                    logger.error("Token missing in Auth header")
                    return jsonify({'message': 'Token is missing or invalid'}), 401
            
            if not token:
                logger.error("Token is None")
                return jsonify({'message': 'Token is missing'}), 401
            
            try:
                # Option 1: Verify locally if we have the JWT secret (Fastest)
                jwt_secret = current_app.config.get('JWT_SECRET_KEY')
                if jwt_secret:
                    # Supabase JWTs are HS256 by default
                    payload = jwt.decode(token, jwt_secret, algorithms=["HS256"], options={"verify_aud": False})
                    # verify_aud=False because audience might vary or be 'authenticated'
                    
                    user_role = payload.get('app_metadata', {}).get('role') or payload.get('role')
                    logger.info(f"Decoded Token. User Role: '{user_role}', Required: '{required_role}'")
                    
                    if user_role != required_role:
                        logger.warning(f"Insufficient permissions: Expected '{required_role}', Got '{user_role}'")
                        return jsonify({'message': 'Insufficient permissions'}), 403
                        
                else:
                    # Option 2: Verify via Supabase API (Slower but always correct)
                    supabase_url = current_app.config.get('SUPABASE_URL')
                    supabase_key = current_app.config.get('SUPABASE_KEY')
                    supabase = create_client(supabase_url, supabase_key)
                    
                    user = supabase.auth.get_user(token)
                    if not user:
                         logger.error("Supabase get_user failed")
                         return jsonify({'message': 'Invalid token'}), 401
                    
                    # Check role from user object or metadata
                    # Typically Supabase user object has role property
                    if user.user.role != required_role:
                         logger.warning(f"Supabase User Role mismatch: Expected '{required_role}', Got '{user.user.role}'")
                         return jsonify({'message': 'Insufficient permissions'}), 403
            
            except jwt.ExpiredSignatureError:
                # Debug logging for expiration
                try:
                    # Decode without verification to see claims
                    claims = jwt.decode(token, options={"verify_signature": False})
                    exp_ts = claims.get('exp')
                    now_ts = datetime.now(timezone.utc).timestamp()
                    logger.error(f"Token expired. Exp: {exp_ts}, Now: {now_ts}, Diff: {exp_ts - now_ts}")
                except Exception as debug_e:
                    logger.error(f"Error debugging expiration: {debug_e}")
                
                return jsonify({'message': 'Token has expired', 'detail': 'Session timed out. Please log in again.'}), 401
            except jwt.InvalidTokenError:
                logger.error("Invalid token error")
                return jsonify({'message': 'Invalid token'}), 401
            except Exception as e:
                logger.error(f"Auth error: {e}")
                return jsonify({'message': f'Authentication error: {str(e)}'}), 401

            return f(*args, **kwargs)
        return decorated_function
    return decorator
