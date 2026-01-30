"""Main web routes"""
from flask import render_template, jsonify
from app.routes import main_bp


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

@main_bp.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@main_bp.route('/login')
def login():
    return render_template('login.html')