"""Main web routes"""
from flask import g, redirect, render_template, request, jsonify
from app.routes import main_bp
from app.security import login_required, role_required
from urllib.parse import urlparse

ADMIN_ROLE = "admin"
REGULAR_ROLE = "regular"

@main_bp.route('/')
def index():
    """Home page"""
    return jsonify({
        'message': 'Welcome to the Flask DevOps Demo Application',
        'status': 'running'
    })

@main_bp.route('/info')
def info():
    return jsonify({
        'app': 'Flask DevOps Demo',
        'framework': 'Flask',
        'language': 'Python'
    })

@main_bp.route('/login')
def login():
    next_path = request.args.get("next", "")
    # validate that next_path is relative URL to prevent open redirect
    if next_path:
        try:
            parsed = urlparse(next_path)
            # allow only relative paths or same-origin absolute URLs
            if parsed.scheme or parsed.netloc or not next_path.startswith('/'):
                next_path = ""
        except Exception:
            next_path = ""
    return render_template("login.html", next_path=next_path)

@main_bp.route('/dashboard')
@login_required
@role_required(REGULAR_ROLE)
def dashboard():
    user = getattr(g, 'current_user', {}) or {}
    user.setdefault('id', '')
    user.setdefault('username', 'User')
    user.setdefault('role', REGULAR_ROLE)
    return render_template("dashboard.html", user=user)

@main_bp.route('/admin')
@login_required
@role_required(ADMIN_ROLE)
def admin():
    user = getattr(g, 'current_user', {}) or {}
    user.setdefault('id', '')
    user.setdefault('username', 'Admin')
    user.setdefault('role', ADMIN_ROLE)
    return render_template("admin_dashboard.html", user=user)

@main_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    return redirect('/login')