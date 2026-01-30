from flask import jsonify, request, current_app
from app.routes import api_bp
from app.services.user_service import UserService
from app.middleware.auth_middleware import role_required
from app.services.auth_service import authenticate_user, create_access_token

@api_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400

    user = authenticate_user(username, password)
    if not user:
        return jsonify({'message': 'Invalid credentials'}), 401

    token = create_access_token(user, current_app.config)
    
    # redirect based on role
    redirect_to = '/dashboard'
    if user.get('role') == 'admin':
        redirect_to = '/admin'

    return jsonify({
        'message': 'Login successful',
        'access_token': token,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'role': user['role']
        },
        'redirect_to': redirect_to
    }), 200

import logging
import datetime
from app.services.auth_service import decode_access_token # Assumption that I can use this or parse header

# Setup Audit Logger
audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.INFO)
audit_handler = logging.FileHandler('audit.log')
audit_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
audit_logger.addHandler(audit_handler)

@api_bp.route('/admin/users', methods=['GET'])
@role_required('admin')
def get_all_users():
    try:
        # Audit Log
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(" ")[1] if auth_header else None
        # Ideally, role_required decorator could pass user info, but decoding again is safe/easy
        try:
             # Just getting username for log
             decoded = decode_access_token(token, current_app.config) if token else {}
             admin_username = decoded.get('username', 'unknown')
        except:
             admin_username = 'unknown'

        audit_logger.info(f"Admin '{admin_username}' accessed user list from IP {request.remote_addr}")

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
        return jsonify({'message': str(e)}), 500

@api_bp.route('/dev/users', methods=['GET']) # Temporary for dev if needed, or remove.
def dev_list_users():
    # Only for development, maybe remove later.
    return jsonify({"message": "Use /admin/users"})
