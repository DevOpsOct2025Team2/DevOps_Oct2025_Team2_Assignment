from flask import Blueprint, render_template, redirect, url_for
from app.security import get_current_user  # or wherever yours is

frontend_bp = Blueprint('frontend', __name__)


@frontend_bp.route('/')
def index():
    # index is public
    return render_template('login.html', title='Login', page='login')


@frontend_bp.route('/dashboard')
def dashboard():
    user = get_current_user()

    # not logged in → redirect
    if not user:
        return redirect(url_for('frontend.index'))

    # admin → go to admin page
    if user.get("role") == "admin":
        return redirect(url_for('main.admin'))

    # normal user
    return render_template(
        'dashboard.html',
        title='Dashboard',
        page='dashboard',
        user=user
    )
