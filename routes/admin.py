from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from models import User

# 创建一个名为 'admin' 的蓝图，所有路由都以 /admin 为前缀
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# 管理员首页
@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    # 非管理员用户不允许访问此页，提示并回到主面板
    if not current_user.is_admin:
        flash('需要管理员权限。')
        return redirect(url_for('main.dashboard'))
    # 查询所有用户记录
    users = User.query.all()
    # 渲染模板，并传入用户列表
    return render_template('admin_dashboard.html', users=users)


# 切换用户锁定状态（锁定或解锁）
@admin_bp.route('/toggle_lock', methods=['POST'])
@login_required   # 要求用户已登录
def toggle_lock():
    # 再次检查管理员权限
    if not current_user.is_admin:
        flash('需要管理员权限。')
        return redirect(url_for('main.dashboard'))
    # 从表单中获取要操作的 user_id
    user_id = int(request.form['user_id'])
    # 查找对应用户，若不存在则返回 404
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

    # 提交数据库事务，保存更改
    db.session.commit()
    # 操作完成后重定向回管理员首页
    return redirect(url_for('admin.admin_dashboard'))
