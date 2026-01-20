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

@main_bp.route('/logout', methods=['GET'])
@login_required
def logout():
    try:
        session.clear()
        
        is_json_request = request.path.startswith('/api/') or request.accept_mimetypes.best == 'application/json'
        
        if is_json_request:
            response = make_response(jsonify({
                'success': True,
                'message': 'You have been logged out successfully.',
                'redirect': '/login'
            }))
        else:
            response = redirect("/login")
        
        # clear primary access token
        auth_cookie_name = current_app.config.get('AUTH_COOKIE_NAME', 'access_token')
        response.set_cookie(
            auth_cookie_name,
            '',
            expires=0,
            httponly=True,
            secure=current_app.config.get('AUTH_COOKIE_SECURE', False),
            samesite=current_app.config.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            path='/',
        )
        
        # clear existing refresh tokens
        response.set_cookie(
            'refresh_token',
            '',
            expires=0,
            httponly=True,
            secure=current_app.config.get('AUTH_COOKIE_SECURE', False),
            samesite=current_app.config.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            path='/',
        )
        
        # clear existing session cookie
        response.set_cookie(
            'session',
            '',
            expires=0,
            httponly=True,
            secure=current_app.config.get('AUTH_COOKIE_SECURE', False),
            samesite=current_app.config.get('AUTH_COOKIE_SAMESITE', 'Lax'),
            path='/',
        )
        
        current_app.logger.info(f'User {g.current_user.get("username", "unknown")} logged out successfully')
        return response
        
    except Exception as e:
        current_app.logger.error(f'Logout error: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'An error occurred during logout. Please try again.',
            'error': str(e) if current_app.debug else 'Internal server error'
        }), 500