"""Main web routes"""
from flask import current_app, g, jsonify, redirect, render_template, request

from app.routes import main_bp
from app.security import login_required, role_required


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
    return render_template("login.html", next_path=next_path)


@main_bp.route('/dashboard')
@login_required
@role_required({"regular"})
def dashboard():
    return render_template("dashboard.html", user=g.current_user)


@main_bp.route('/admin')
@login_required
@role_required({"admin"})
def admin():
    return render_template("admin.html", user=g.current_user)


@main_bp.route('/logout')
def logout():
    response = redirect("/login")
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
