import logging
from flask import current_app, jsonify, request, g, session
from app.routes import api_bp
from app.security import login_required
from app.services import auth_service
from app.services.user_service import UserService
from app.audit.log import log_admin_action

# audit logging
audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.INFO)
if not audit_logger.handlers:
    audit_handler = logging.FileHandler('audit.log')
    audit_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    audit_logger.addHandler(audit_handler)

def _get_current_user_info():
    user = g.get("current_user")
    if isinstance(user, dict):
        return user.get("username", "unknown"), user.get("role")
    else:
        username = getattr(user, "username", "unknown") if user else "unknown"
        role = getattr(user, "role", None) if user else None
        return username, role


@api_bp.route("/auth/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not username or not password:
        return jsonify({"error": "invalid_request", "message": "Username and password are required."}), 400

    try:
        user = auth_service.authenticate_user(username, password)
    except RuntimeError as e:
        current_app.logger.error(f"Authentication service error: {str(e)}")
        return jsonify({"error": "server_configuration", "message": "Authentication service is not configured."}), 500
    
    if not user:
        audit_logger.warning(f"Failed login attempt for username: {username}")
        return jsonify({"error": "invalid_credentials", "message": "Invalid username or password."}), 401

    token = auth_service.create_access_token(user, current_app.config)
    redirect_to = "/admin" if user.get("role") == "admin" else "/dashboard"

    response = jsonify({
        "message": "Login successful.",
        "role": user.get("role"),
        "redirect_to": redirect_to,
    })
    
    response.set_cookie(
        current_app.config.get("AUTH_COOKIE_NAME", "access_token"),
        token,
        httponly=True,
        secure=current_app.config.get("AUTH_COOKIE_SECURE", False),
        samesite=current_app.config.get("AUTH_COOKIE_SAMESITE", "Lax"),
        max_age=current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", 3600),
        path="/",
    )
        # Sanitize values before logging to prevent log injection
        safe_admin_username = str(admin_username).replace('\r', '').replace('\n', '')
        raw_remote_addr = request.remote_addr or 'unknown'
        safe_remote_addr = str(raw_remote_addr).replace('\r', '').replace('\n', '')
    audit_logger.info(f"User {username} logged in successfully from IP {request.remote_addr}")
        audit_logger.info(f"Admin '{safe_admin_username}' accessed user list from IP {safe_remote_addr}")

    return response


@api_bp.route("/auth/logout", methods=["GET", "POST"])
@login_required
def logout():    
    username, _ = _get_current_user_info()

    try:
        session.clear()

             # Log the internal error detail but return a generic message to the client
             audit_logger.error(
                 f"Failed to fetch users for admin '{admin_username}' from IP {request.remote_addr}: {result.get('error')}"
             )
             return jsonify({'message': 'An internal error occurred while fetching users'}), 500
            "success": True,
            "message": "You have been logged out successfully."
        })
        # Log unexpected exceptions and return a generic message
        audit_logger.exception(
            f"Unexpected error in get_all_users for admin '{admin_username}' from IP {request.remote_addr}"
        )
        return jsonify({'message': 'An internal server error occurred'}), 500
        auth_cookie_name = current_app.config.get("AUTH_COOKIE_NAME", "access_token")
        cookies_to_clear = [auth_cookie_name, "refresh_token", "session"]
        
        for cookie_name in cookies_to_clear:
            response.set_cookie(
                cookie_name,
                "",
                expires=0,
                httponly=True,
                secure=current_app.config.get("AUTH_COOKIE_SECURE", False),
                samesite=current_app.config.get("AUTH_COOKIE_SAMESITE", "Lax"),
                path="/",
            )
            
        audit_logger.info(f"User {username} logged out successfully from IP {request.remote_addr}")
        return response
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return jsonify({
            "success": False,
            "message": "An error occurred during logout. Please try again.",
            "error": str(e) if current_app.debug else "Internal server error"
        }), 500


@api_bp.route("/auth/me", methods=["GET"])
@login_required
def me():
    return jsonify({"user": g.current_user})


@api_bp.route('/users', methods=['POST'])
@login_required
def create_user():
    username_actor, user_role = _get_current_user_info()

    if user_role != 'admin':
        audit_logger.warning(f"Unauthorized user creation attempt by {username_actor} from IP {request.remote_addr}")
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'regular').strip().lower()

    # validate username
    if not (3 <= len(username) <= 32):
        return jsonify({'error': 'Username must be 3-32 characters.'}), 400
    if not username.replace('_', '').isalnum():
        return jsonify({'error': 'Username can only contain letters, numbers, and underscores.'}), 400

    # validate role
    if role not in ['regular', 'admin']:
        return jsonify({'error': 'Invalid role. Must be "regular" or "admin".'}), 400
    
    # validate password
    if not password or len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters with letters and numbers.'}), 400
    
    if not any(c.isdigit() for c in password) or not any(c.isalpha() for c in password):
        return jsonify({'error': 'Password must be at least 8 characters with letters and numbers.'}), 400

    try:
        supabase = auth_service.get_supabase_client()
        if not supabase:
            current_app.logger.error("Supabase client is None")
            return jsonify({'error': 'Database service unavailable.'}), 500
        
        # hash password
        try:
            password_hash = auth_service.hash_password(password)
        except Exception as hash_err:
            current_app.logger.error(f"Password hashing error: {str(hash_err)}")
            return jsonify({'error': 'Failed to process password.'}), 500

        # insert user
        try:
            current_app.logger.debug(f"Attempting to insert user: {username} with role: {role}")
            
            insert_data = {
                "username": username,
                "password_hash": password_hash,
                "role": role,
                "is_active": True
            }
            current_app.logger.debug(f"Insert data: {insert_data}")
            
            result = supabase.table("users").insert(insert_data).execute()
            
            current_app.logger.info(f"User {username} inserted successfully with role {role}")
            
        except Exception as insert_err:
            error_str = str(insert_err)
            current_app.logger.error(f"User insert error: {error_str}", exc_info=True)
            
            # Check for common errors
            if "check constraint" in error_str.lower() or "role" in error_str.lower():
                return jsonify({'error': 'Invalid role value. Allowed: "regular" or "admin".'}), 400
            elif "duplicate" in error_str.lower() or "unique" in error_str.lower():
                return jsonify({'error': 'Username already exists.'}), 409
            elif "not null" in error_str.lower() or "required" in error_str.lower():
                return jsonify({'error': 'Missing required fields.'}), 400
            else:
                return jsonify({'error': 'Failed to create user in database.'}), 500

        log_admin_action(username_actor, f"Created user {username} with role {role}")
        audit_logger.info(f"Admin {username_actor} created user {username} with role {role}")

        return jsonify({'message': 'User created successfully.'}), 201

    except Exception as e:
        current_app.logger.error(f"User creation error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to create user. Server error.'}), 500


@api_bp.route('/admin/users', methods=['GET'])
@login_required
def get_all_users():
    # fetch all users with pagination, search, and sorting for admins
    username_actor, user_role = _get_current_user_info()
    
    if user_role != 'admin':
        audit_logger.warning(f"Unauthorized user list access attempt by {username_actor}")
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        audit_logger.info(f"Admin '{username_actor}' accessed user list from IP {request.remote_addr}")

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        sort_by = request.args.get('sort_by', 'created_at')
        order = request.args.get('order', 'desc')
        
        user_service = UserService()
        result = user_service.get_all_users(
            page=page, 
            per_page=per_page,
            search_query=search,
            sort_by=sort_by,
            sort_order=order
        )
        
        if 'error' in result:
            return jsonify({'message': result['error']}), 500
             
        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching users: {str(e)}")
        return jsonify({'message': 'Failed to fetch users'}), 500