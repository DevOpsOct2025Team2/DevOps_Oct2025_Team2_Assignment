from functools import wraps

import jwt
from flask import current_app, g, jsonify, redirect, request, url_for

from app.services.auth_service import decode_access_token


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = _get_token()
        if not token:
            return _unauthorized("Authentication required.")

        try:
            payload = decode_access_token(token, current_app.config)
        except jwt.ExpiredSignatureError:
            return _unauthorized("Session expired. Please log in again.")
        except jwt.InvalidTokenError:
            return _unauthorized("Invalid session. Please log in again.")

        g.current_user = payload
        return view(*args, **kwargs)

    return wrapper


def role_required(roles):
    if isinstance(roles, str):
        roles = {roles.lower()}
    else:
        roles = {role.lower() for role in roles}

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if not user:
                return _unauthorized("Authentication required.")

            role = (user.get("role") or "").lower()
            if role not in roles:
                if _wants_json():
                    return _forbidden("Insufficient permissions.")
                return _redirect_for_role(role)

            return view(*args, **kwargs)

        return wrapper

    return decorator


def _get_token():
    cookie_name = current_app.config.get("AUTH_COOKIE_NAME", "access_token")
    token = request.cookies.get(cookie_name)
    if token:
        return token

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


def _wants_json():
    if request.path.startswith("/api/"):
        return True
    best = request.accept_mimetypes.best or ""
    return "json" in best


def _unauthorized(message):
    if _wants_json():
        return jsonify({"error": "unauthorized", "message": message}), 401
    return redirect(url_for("main.login", next=request.path))


def _forbidden(message):
    if _wants_json():
        return jsonify({"error": "forbidden", "message": message}), 403
    return redirect(url_for("main.login", next=request.path))


def _redirect_for_role(role):
    if role == "admin":
        return redirect(url_for("main.admin"))
    if role == "regular":
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))
