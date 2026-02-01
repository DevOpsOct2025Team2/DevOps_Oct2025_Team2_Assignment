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
    
    audit_logger.info(f"User {username} logged in successfully from IP {request.remote_addr}")
    return response


@api_bp.route("/auth/logout", methods=["GET", "POST"])
@login_required
def logout():    
    username, _ = _get_current_user_info()

    try:
        session.clear()

        response = jsonify({
            "success": True,
            "message": "You have been logged out successfully."
        })
        
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
    role = data.get('role', 'user')

    # validate username
    if not (3 <= len(username) <= 32):
        return jsonify({'error': 'Username must be 3-32 characters.'}), 400
    if not username.replace('_', '').isalnum():
        return jsonify({'error': 'Username can only contain letters, numbers, and underscores.'}), 400

    # validate role
    if role not in ['user', 'admin']:
        return jsonify({'error': 'Invalid role.'}), 400
    
    # validate password
    if not password or len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters with letters and numbers.'}), 400
    
    if not any(c.isdigit() for c in password) or not any(c.isalpha() for c in password):
        return jsonify({'error': 'Password must be at least 8 characters with letters and numbers.'}), 400

    try:
        supabase = auth_service.get_supabase_client()
        # check if username already exists
        try:
            existing = supabase.table("users").select("id").eq("username", username).single().execute()
            if existing.data:
                return jsonify({'error': 'Username already exists.'}), 409
        except Exception as check_err:
            if "No rows found" not in str(check_err):
                raise
        # hash password
        password_hash = auth_service.hash_password(password)

        # insert user
        result = supabase.table("users").insert({
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "is_active": True
        }).execute()

        log_admin_action(username_actor, f"Created user {username} with role {role}")
        audit_logger.info(f"Admin {username_actor} created user {username} with role {role}")

        return jsonify({'message': 'User created successfully.'}), 201

    except Exception as e:
        current_app.logger.error(f"User creation error: {str(e)}")
        return jsonify({'error': 'Failed to create user.'}), 500


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