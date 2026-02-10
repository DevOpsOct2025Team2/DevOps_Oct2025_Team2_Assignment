
from flask import Blueprint, render_template

frontend_bp = Blueprint('frontend', __name__)

@frontend_bp.route('/')
def index():
    return render_template('login.html', title='Login', page='login')

@frontend_bp.route('/dashboard')
def dashboard():
    return render_template('admin_dashboard.html', title='Dashboard', page='dashboard')