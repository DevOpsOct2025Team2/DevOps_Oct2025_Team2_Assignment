from flask import current_app, jsonify, request

from app.routes import api_bp
from app.security import login_required
from app.services import auth_service


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


@api_bp.route("/auth/logout", methods=["POST"])
def logout():
    response = jsonify({"message": "Logged out."})
    response.set_cookie(
        current_app.config.get("AUTH_COOKIE_NAME", "access_token"),
        "",
        expires=0,
        httponly=True,
        secure=current_app.config.get("AUTH_COOKIE_SECURE", False),
        samesite=current_app.config.get("AUTH_COOKIE_SAMESITE", "Lax"),
        path="/",
    )
    return response


@api_bp.route("/auth/me", methods=["GET"])
@login_required
def me():
    from flask import g

    return jsonify({"user": g.current_user})
