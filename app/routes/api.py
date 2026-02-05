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


def _sanitize_for_log(value):
    """
    Remove characters that can break log structure (like newlines)
    from user-controlled values before logging.
    """
    if value is None:
        return ""
    # Ensure we are working with a string and strip CR/LF characters
    text = str(value)
    return text.replace("\r", "").replace("\n", "")


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
    except RuntimeError:
        return (
            jsonify({
                    "error": "server_configuration",
                    "message": "Authentication service is not configured.",
                }),
            500,
        )
    if not user:
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
    # improved fix
    # Sanitize values before logging to prevent log injection
    safe_username = username.replace('\r', '').replace('\n', '')
    safe_ip = (request.remote_addr or "unknown").replace('\r', '').replace('\n', '')
    audit_logger.info("User %s logged in from IP %s", safe_username, safe_ip)
    return response

@api_bp.route("/auth/logout", methods=["GET", "POST"])
@login_required
def logout():    
    username, _ = _get_current_user_info()
    try:
        session.clear()
        
        auth_cookie_name = current_app.config.get("AUTH_COOKIE_NAME", "access_token")
        cookies_to_clear = [auth_cookie_name, "refresh_token", "session"]
        
        response = jsonify({
            "success": True,
            "message": "You have been logged out successfully."
        })
        
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
            
        audit_logger.info("User %s logged out", username)
        return response, 200
      
    except Exception:
        audit_logger.exception("Unexpected logout error for %s", username)
        return jsonify({
            "success": False,
            "message": "An internal server error occured.",
        }), 500

@api_bp.route("/auth/me", methods=["GET"])
@login_required
def me():
    from flask import g
    return jsonify({"user": g.current_user})


@api_bp.route('/auth/users', methods=['POST'])
@login_required
def create_user():
    # improved fix
    username_actor, user_role = _get_current_user_info()

    if user_role != 'admin':
        remote_addr = (request.remote_addr or "").replace("\r", "").replace("\n", "")
        audit_logger.warning("Unauthorized user creation attempt by %s from IP %s", username_actor, remote_addr)
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
        except Exception:
            current_app.logger.error("Password hashing error", exc_info=True)
            return jsonify({'error': 'Failed to process password.'}), 500

        # insert user
        try:
            current_app.logger.debug("Attempting to insert user: %s with role: %s", username, role)
            
            insert_data = {
                "username": username,
                "password_hash": password_hash,
                "role": role,
                "is_active": True
            }            
            result = supabase.table("users").insert(insert_data).execute()
            
        except Exception as insert_err:
            error_str = str(insert_err).lower()
            current_app.logger.error("User insert error:", exc_info=True)
            # improved fix 
            if "duplicate" in error_str or "unique" in error_str:
                return jsonify({'error': 'Username already exists.'}), 409
            elif "check constraint" in error_str or "role" in error_str:
                return jsonify({'error': 'Invalid role value.'}), 400 
            else:
                return jsonify({'error': 'Failed to create user in database.'}), 500

        log_admin_action(username_actor, f"Created user {username} with role {role}")
        safe_username = _sanitize_for_log(username)
        safe_role = _sanitize_for_log(role)
        audit_logger.info("Admin %s created user %s with role %s", username_actor, safe_username, safe_role)

        return jsonify({'message': 'User created successfully.'}), 201

    except Exception:
        current_app.logger.error("User creation error", exc_info=True)
        return jsonify({'error': 'Failed to create user. Server error.'}), 500


@api_bp.route('/admin/users', methods=['GET'])
@login_required
def get_all_users():
    # fetch all users with pagination, search, and sorting for admins
    username_actor, user_role = _get_current_user_info()
    
    if user_role != 'admin':
        audit_logger.warning("Unauthorized user list access attempt by %s", username_actor)
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        remote_addr = (request.remote_addr or "").replace("\r", "").replace("\n", "")
        audit_logger.info("Admin %s accessed user list from IP %s", username_actor, remote_addr)

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
    except Exception:
        current_app.logger.error("Error fetching users", exc_info=True)
        return jsonify({'message': 'Failed to fetch users'}), 500
