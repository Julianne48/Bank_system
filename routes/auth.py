from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from extensions import db, mail
from models import User
from flask_login import current_user, login_user
from datetime import datetime, timedelta

# Blueprint 前缀可根据需要调整
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def get_serializer():
    """在请求上下文中安全创建 Serializer"""
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册，请直接登录。')
            return redirect(url_for('auth.login'))

        hashed_pw = generate_password_hash(password)
        user = User(email=email, password_hash=hashed_pw, is_verified=False)
        db.session.add(user)
        db.session.commit()

        # 生成并发送验证邮件
        serializer = get_serializer()
        token = serializer.dumps(email, salt='email-confirm-salt')
        verify_url = url_for('auth.verify_email', token=token, _external=True)

        msg = Message(subject="[银行系统] 邮箱验证",
                      sender=current_app.config['MAIL_DEFAULT_SENDER'],
                      recipients=[email])
        msg.body = f'请点击此链接完成邮箱验证：{verify_url}'
        mail.send(msg)

        flash('注册成功！已发送验证邮件，请检查邮箱。')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    # 如果用户已登录，优先使用 current_user
    if current_user.is_authenticated:
        user = current_user
    else:
        # 未登录时，从表单获取 email
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('该邮箱未注册。')
            return redirect(url_for('auth.login'))

    if user.is_verified:
        flash('该邮箱已完成验证，无需重发。')
        return redirect(url_for('auth.login'))

    # 生成并发送验证邮件
    serializer = get_serializer()
    token = serializer.dumps(user.email, salt='email-confirm-salt')
    verify_url = url_for('auth.verify_email', token=token, _external=True)

    msg = Message(
        subject="[银行系统] 重发邮箱验证",
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user.email]
    )
    msg.body = f'请点击此链接完成邮箱验证：\n\n{verify_url}'
    mail.send(msg)

    flash(f'验证邮件已发送到 {user.email}，请查收。')
    return redirect(url_for('auth.login'))

@auth_bp.route('/verify/<token>')
def verify_email(token):
    serializer = get_serializer()
    try:
        email = serializer.loads(token, salt='email-confirm-salt', max_age=3600)
    except Exception:
        flash('验证链接无效或已过期。')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('用户不存在。')
        return redirect(url_for('auth.register'))

    user.is_verified = True
    db.session.commit()
    flash('邮箱验证成功，请登录。')
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('用户不存在。')
            return redirect(url_for('auth.login'))

        if user.is_locked:
            flash('账户已锁定，请联系管理员解锁。')
            return redirect(url_for('auth.login'))

        now = datetime.now()
        if user.first_failed_at and now - user.first_failed_at > timedelta(days=1):
            user.failed_login_attempts = 0
            user.first_failed_at = None

        if check_password_hash(user.password_hash, password):
            if not user.is_verified:
                flash('请先完成邮箱验证。')
                return redirect(url_for('auth.login'))

            user.failed_login_attempts = 0
            user.first_failed_at = None
            db.session.commit()

            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            if user.failed_login_attempts == 0:
                user.first_failed_at = now
            user.failed_login_attempts += 1

            if user.failed_login_attempts >= 5:
                user.is_locked = True
                flash('密码错误已达 5 次，账户已锁定，请联系管理员。')
            else:
                flash(f'密码错误，第 {user.failed_login_attempts} 次失败（5 次后锁定）。')

            db.session.commit()
            return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    from flask_login import logout_user
    logout_user()
    flash('已安全登出。')
    return redirect(url_for('auth.login'))