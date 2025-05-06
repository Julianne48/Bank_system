from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import Account, User

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('需要管理员权限。')
        return redirect(url_for('main.dashboard'))
    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

@admin_bp.route('/toggle_lock', methods=['POST'])
@login_required
def toggle_lock():
    if not current_user.is_admin:
        flash('需要管理员权限。')
        return redirect(url_for('main.dashboard'))
    user_id = int(request.form['user_id'])
    user = User.query.get_or_404(user_id)
    # 解锁时重置失败计数
    if user.is_locked:
        user.is_locked = False
        user.failed_login_attempts = 0
        user.first_failed_at = None
        flash(f'{user.email} 已解锁，失败次数已重置。')
    else:
        user.is_locked = True
        flash(f'{user.email} 已锁定。')

    db.session.commit()
    return redirect(url_for('admin.admin_dashboard'))
