from flask import current_app, jsonify, request, g, session
from app.routes import api_bp
from app.security import login_required
from app.services import auth_service
from app.audit.log import log_admin_action

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
            jsonify(
                {
                    "error": "server_configuration",
                    "message": "Authentication service is not configured.",
                }
            ),
            500,
        )
    if not user:
        return jsonify({"error": "invalid_credentials", "message": "Invalid username or password."}), 401

    token = auth_service.create_access_token(user, current_app.config)
    redirect_to = "/admin" if user.get("role") == "admin" else "/dashboard"

    response = jsonify(
        {
            "message": "Login successful.",
            "role": user.get("role"),
            "redirect_to": redirect_to,
        }
    )
    response.set_cookie(
        current_app.config.get("AUTH_COOKIE_NAME", "access_token"),
        token,
        httponly=True,
        secure=current_app.config.get("AUTH_COOKIE_SECURE", False),
        samesite=current_app.config.get("AUTH_COOKIE_SAMESITE", "Lax"),
        max_age=current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", 3600),
        path="/",
    )
    return response


@api_bp.route("/auth/logout", methods=["GET", "POST"])
@login_required
def logout():    
    user = g.get("current_user")
    if isinstance(user, dict):
        username = user.get("username", "unknown")
    else:
        username = getattr(user, "username", "unknown") if user else "unknown"

    try:
        session.clear()

        response = jsonify({
            "success": True,
            "message": "You have been logged out successfully."
        })
        
        # clear all auth cookies
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
            
        current_app.logger.info(f'User {username} logged out successfully')
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
    from flask import g

    return jsonify({"user": g.current_user})


@api_bp.route('/users', methods=['POST'])
@login_required
def create_user():
    user = g.get("current_user")
    if isinstance(user, dict):
        user_role = user.get("role")
        username_actor = user.get("username", "unknown")
    else:
        user_role = getattr(user, "role", None)
        username_actor = getattr(user, "username", "unknown")

    if user_role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    email = data.get('username', '').strip()  # Using email as username
    password = data.get('password', '')
    role = data.get('role', 'user')

    # validate email
    if not (3 <= len(email) <= 32):
        return jsonify({'error': 'Email must be 3-32 characters.'}), 400
    # validate role
    if not (role in ['user', 'admin']):
        return jsonify({'error': 'Invalid role.'}), 400
    # validate password
    if not password or len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters with letters and numbers.'}), 400
    if not any(c.isdigit() for c in password) or not any(c.isalpha() for c in password):
        return jsonify({'error': 'Password must be at least 8 characters with letters and numbers.'}), 400
    try:
        supabase = auth_service()
        
        # Create user via Supabase Admin API
        response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "role": role
            }
        })
        
        # audit log
        log_admin_action(username_actor, f"Created user {email} with role {role}")
        
        return jsonify({'message': 'User created successfully.'}), 201
        
    except Exception as e:
        error_message = str(e)
        if 'already registered' in error_message.lower():
            return jsonify({'error': 'Username already exists.'}), 409
        
        current_app.logger.error(f"User creation error: {error_message}")
        return jsonify({'error': 'Failed to create user.'}), 500