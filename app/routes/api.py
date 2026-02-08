import logging, os
from flask import current_app, jsonify, request, g, session
from werkzeug.utils import secure_filename
from app.routes import api_bp
from app.security import login_required
from app.services import auth_service
from app.services.user_service import UserService
from app.services.file_service import FileService
from app.audit.log import log_admin_action

# audit logging
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)
if not audit_logger.handlers:
    audit_handler = logging.FileHandler('audit.log')
    audit_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    audit_logger.addHandler(audit_handler)

logger = logging.getLogger(__name__)

def _sanitize_for_log(value):
    """Remove char that can break log structure from user-controlled values before logging"""
    if value is None:
        return ""
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

def _get_current_user_id():
    user = g.get("current_user")
    if isinstance(user, dict):
        return str(user.get("sub") or user.get("id") or "").strip()
    if not user:
        return ""
    return str(getattr(user, "sub", "") or getattr(user, "id", "")).strip()

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'zip'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api_bp.route("/auth/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not username or not password:
        return (
            jsonify(
                {"error": "invalid_request", "message": "Username and password are required."}
            ),
            400,
        )

    try:
        user = auth_service.authenticate_user(username, password)
    except RuntimeError:
        return jsonify({
            "error": "server_configuration",
            "message": "Authentication service is not configured.",
        }), 500
    
    if not user:
        return (
            jsonify({"error": "invalid_credentials", "message": "Invalid username or password."}),
            401,
        )

    token = auth_service.create_access_token(user, current_app.config)
    
    user_role = user.get("role", "").lower()
    if user_role == "admin":
        redirect_to = "/admin"
    else:
        redirect_to = "/dashboard"

    response = jsonify({
        "message": "Login successful.",
        "role": user_role,
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
    safe_username = _sanitize_for_log(username)
    safe_ip = _sanitize_for_log(request.remote_addr or "unknown")
    audit_logger.info("User %s logged in from IP %s", safe_username, safe_ip)

    return response


@api_bp.route("/auth/logout", methods=["GET", "POST"])
@login_required
def logout():
    username, _ = _get_current_user_info()
    try:
        session.clear()

        response = jsonify({
            "success": True,
            "message": "You have been logged out successfully.",
            "redirect_to": "/login"
        })

        auth_cookie_name = current_app.config.get("AUTH_COOKIE_NAME", "access_token")
        cookies_to_clear = [auth_cookie_name, "refresh_token", "session"]

        for cookie_name in cookies_to_clear:
            response.set_cookie(
                cookie_name,
                "",
                expires=0,
                max_age=0,
                httponly=True,
                secure=current_app.config.get("AUTH_COOKIE_SECURE", False),
                samesite=current_app.config.get("AUTH_COOKIE_SAMESITE", "Lax"),
                path="/",
            )

        audit_logger.info("User %s logged out", _sanitize_for_log(username))
        return response, 200

    except Exception:
        audit_logger.exception("Unexpected logout error for %s", _sanitize_for_log(username))
        return jsonify({
            "success": False,
            "message": "An internal server error occurred.",
        }), 500

@api_bp.route("/auth/me", methods=["GET"])
@login_required
def me():
    from flask import g

    return jsonify({"user": g.current_user})


@api_bp.route("/auth/users", methods=["POST"])
@login_required
def create_user():
    username_actor, user_role = _get_current_user_info()

    if user_role != "admin":
        remote_addr = _sanitize_for_log(request.remote_addr or "")
        audit_logger.warning(
            "Unauthorized user creation attempt by %s from IP %s",
            _sanitize_for_log(username_actor),
            remote_addr,
        )
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body required"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "regular").strip().lower()

    # validate username
    if not (3 <= len(username) <= 32):
        return jsonify({"error": "Username must be 3-32 characters."}), 400
    if not username.replace("_", "").isalnum():
        return jsonify(
            {"error": "Username can only contain letters, numbers, and underscores."}
        ), 400

    # validate role
    if role not in ["regular", "admin"]:
        return jsonify({"error": 'Invalid role. Must be "regular" or "admin".'}), 400

    # validate password
    if not password or len(password) < 8:
        return jsonify(
            {"error": "Password must be at least 8 characters with letters and numbers."}
        ), 400

    if not any(c.isdigit() for c in password) or not any(c.isalpha() for c in password):
        return jsonify(
            {"error": "Password must be at least 8 characters with letters and numbers."}
        ), 400

    try:
        supabase = auth_service.get_supabase_client()
        if not supabase:
            current_app.logger.error("Supabase client is None")
            return jsonify({"error": "Database service unavailable."}), 500

        # hash password
        try:
            password_hash = auth_service.hash_password(password)
        except Exception:
            current_app.logger.error("Password hashing error", exc_info=True)
            return jsonify({"error": "Failed to process password."}), 500

        # insert user
        try:
            current_app.logger.debug(
                "Attempting to insert user: %s with role: %s", username, role
            )

            insert_data = {
                "username": username,
                "password_hash": password_hash,
                "role": role,
                "is_active": True,
            }
            supabase.table("users").insert(insert_data).execute()

        except Exception as insert_err:
            error_str = str(insert_err).lower()
            current_app.logger.error("User insert error:", exc_info=True)
            if "duplicate" in error_str or "unique" in error_str:
                return jsonify({"error": "Username already exists."}), 409
            elif "check constraint" in error_str or "role" in error_str:
                return jsonify({"error": "Invalid role value."}), 400
            else:
                return jsonify({"error": "Failed to create user in database."}), 500

        log_admin_action(username_actor, f"Created user {username} with role {role}")

        audit_logger.info(
            "Admin %s created user %s with role %s",
            _sanitize_for_log(username_actor),
            _sanitize_for_log(username),
            _sanitize_for_log(role),
        )

        return jsonify({"message": "User created successfully."}), 201

    except Exception:
        current_app.logger.error("User creation error", exc_info=True)
        return jsonify({"error": "Failed to create user. Server error."}), 500


@api_bp.route("/admin/users", methods=["GET"])
@login_required
def get_all_users():
    username_actor, user_role = _get_current_user_info()

    if user_role != "admin":
        audit_logger.warning(
            "Unauthorized user list access attempt by %s", _sanitize_for_log(username_actor)
        )
        return jsonify({"error": "Unauthorized"}), 403

    try:
        remote_addr = _sanitize_for_log(request.remote_addr or "")
        audit_logger.info(
            "Admin %s accessed user list from IP %s",
            _sanitize_for_log(username_actor),
            remote_addr,
        )

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "")
        sort_by = request.args.get("sort_by", "created_at")
        order = request.args.get("order", "desc")

        user_service = UserService()
        result = user_service.get_all_users(
            page=page,
            per_page=per_page,
            search_query=search,
            sort_by=sort_by,
            sort_order=order,
        )

        if "error" in result:
            return jsonify({"message": result["error"]}), 500

        return jsonify(result), 200
    except Exception:
        current_app.logger.logger.error("Error fetching users", exc_info=True)
        return jsonify({'message': 'Failed to fetch users'}), 500


@api_bp.route('/files/me', methods=['GET'])
@login_required
def get_user_files():
    username_actor, user_role = _get_current_user_info()
    user_id = g.current_user.get('id') if isinstance(g.current_user, dict) else getattr(g.current_user, 'id', None)
    
    if user_role == 'admin':
        audit_logger.warning("Admin user %s attempted to access /files/me endpoint", username_actor)
        return jsonify({'error': 'Unauthorized'}), 403
    
    if not user_id:
        audit_logger.warning("User %s attempted to access files without valid user_id", username_actor)
        return jsonify({'error': 'Invalid user session'}), 400
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        sort_by = request.args.get('sort_by', 'created_at')
        order = request.args.get('order', 'desc')
        
        # check pagination
        if page < 1 or per_page < 1 or per_page > 100:
            return jsonify({'error': 'Invalid pagination parameters'}), 400
        
        supabase = auth_service.get_supabase_client()
        if not supabase:
            current_app.logger.error("Supabase client is None")
            return jsonify({'error': 'Database service unavailable'}), 500
        
        file_service = FileService(supabase)
        result = file_service.get_user_files(
            user_id=user_id,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=order
        )
        
        if 'error' in result:
            return jsonify({'message': result['error']}), 500
        
        safe_user = _sanitize_for_log(username_actor)
        safe_page = int(page)
        audit_logger.info("User %s retrieved file list (page %d)", safe_user, safe_page)
        
        return jsonify(result), 200
    except Exception:
        current_app.logger.error("Error retrieving user files", exc_info=True)
        return jsonify({'message': 'Failed to retrieve files'}), 500


@api_bp.route('/files/<file_id>', methods=['DELETE'])
@login_required
def delete_file(file_id):
    username_actor, user_role = _get_current_user_info()
    user_id = g.current_user.get('id') if isinstance(g.current_user, dict) else getattr(g.current_user, 'id', None)
    
    if user_role == 'admin':
        audit_logger.warning("Admin user %s attempted to delete file via /files endpoint", username_actor)
        return jsonify({'error': 'Unauthorized'}), 403
    
    if not user_id:
        return jsonify({'error': 'Invalid user session'}), 400
    
    try:
        supabase = auth_service.get_supabase_client()
        if not supabase:
            return jsonify({'error': 'Database service unavailable'}), 500
        
        file_service = FileService(supabase)
        result = file_service.delete_file(user_id=user_id, file_id=file_id)
        
            safe_file_id = _sanitize_for_log(file_id)
            audit_logger.warning("User %s attempted unauthorized file deletion for file_id: %s", username_actor, safe_file_id)
            audit_logger.warning("User %s attempted unauthorized file deletion for file_id: %s", username_actor, file_id)
            return jsonify(result), 403
        
        safe_user = _sanitize_for_log(username_actor)
        audit_logger.info("User %s deleted file %s", safe_user, file_id)
        
        return jsonify(result), 200
    except Exception:
        current_app.logger.error("Error deleting file", exc_info=True)
        return jsonify({'error': 'Failed to delete file'}), 500

@api_bp.route('/files/upload', methods=['POST'])
@login_required
def upload_file():
    username_actor, user_role = _get_current_user_info()
    user_id = g.current_user.get('id') if isinstance(g.current_user, dict) else getattr(g.current_user, 'id', None)
    
    if user_role == 'admin':
        audit_logger.warning("Admin user %s attempted to upload file via /files endpoint", username_actor)
        return jsonify({'error': 'Unauthorized'}), 403
    
    if not user_id:
        return jsonify({'error': 'Invalid user session'}), 400
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)
        
        if file_length > MAX_FILE_SIZE:
            return jsonify({'error': 'File exceeds maximum size limit'}), 400
        
        filename = secure_filename(file.filename)
        file_data = file.read()
        
        supabase = auth_service.get_supabase_client()
        if not supabase:
            return jsonify({'error': 'Database service unavailable'}), 500
        
        file_service = FileService(supabase)
        result = file_service.upload_file(
            user_id=user_id,
            filename=filename,
            file_data=file_data,
            file_type=file.mimetype,
            username=username_actor
        )
        
        if 'error' in result:
            return jsonify(result), 500
        
        safe_user = _sanitize_for_log(username_actor)
        audit_logger.info("User %s uploaded file %s", safe_user, filename)
        
        return jsonify(result), 201
    except Exception:
        current_app.logger.error("Error uploading file", exc_info=True)
        return jsonify({'error': 'Failed to upload file'}), 500

@api_bp.route("/admin/users/<user_id>", methods=["DELETE"])
@login_required
def delete_user(user_id):
    username_actor, user_role = _get_current_user_info()

    if user_role != "admin":
        remote_addr = _sanitize_for_log(request.remote_addr or "")
        audit_logger.warning(
            "Unauthorized user deletion attempt by %s from IP %s",
            _sanitize_for_log(username_actor),
            remote_addr,
        )
        return jsonify({"error": "Unauthorized"}), 403

    target_user_id = (user_id or "").strip()
    if not target_user_id:
        return jsonify({"error": "User id is required."}), 400

    current_user_id = _get_current_user_id()
    if current_user_id and target_user_id == current_user_id:
        audit_logger.warning(
            "Admin %s attempted to delete their own account", _sanitize_for_log(username_actor)
        )
        return jsonify({"error": "You cannot delete your own account."}), 400

    try:
        user_service = UserService()
        existing_user = user_service.get_user_by_id(target_user_id)

        if not existing_user:
            return jsonify({"error": "User not found."}), 404

        if current_user_id and str(existing_user.get("id", "")).strip() == current_user_id:
            audit_logger.warning(
                "Admin %s attempted to delete their own account", _sanitize_for_log(username_actor)
            )
            return jsonify({"error": "You cannot delete your own account."}), 400

        deleted_user = user_service.delete_user_by_id(target_user_id)
        if not deleted_user:
            current_app.logger.error(
                "Delete operation returned no deleted user for id=%s", target_user_id
            )
            return jsonify({"error": "Failed to delete user."}), 500

        safe_actor = _sanitize_for_log(username_actor)
        safe_target_username = _sanitize_for_log(existing_user.get("username") or target_user_id)
        safe_target_id = _sanitize_for_log(target_user_id)
        remote_addr = _sanitize_for_log(request.remote_addr or "")

        log_admin_action(username_actor, f"Deleted user {safe_target_username} (id={safe_target_id})")
        audit_logger.info(
            "Admin %s deleted user %s (id=%s) from IP %s",
            safe_actor,
            safe_target_username,
            safe_target_id,
            remote_addr,
        )
        return jsonify({"message": "User deleted successfully."}), 200
    except Exception:
        current_app.logger.error("User deletion error", exc_info=True)
        return jsonify({"error": "Failed to delete user. Server error."}), 500
