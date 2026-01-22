"""Main web routes"""
from flask import g, redirect, render_template, request, jsonify
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

@main_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    return redirect('/login')