from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from extensions import db, mail
from models import User
from flask_login import current_user, login_user, login_required
from datetime import datetime, timedelta
import random

# 创建认证蓝图，所有路由前缀为 /auth
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def generate_code():
    #生成6位随机验证码
    return f"{random.randint(0, 999999):06d}"


### 注册：生成并发送邮箱验证码 ###
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 从表单获取用户输入
        email = request.form['email']
        password = request.form['password']
        id_card = request.form['id_card']
        student_number = request.form['student_number']
        name = request.form['name']
        gender = request.form['gender']
        phone_number = request.form['phone_number']
        code = generate_code()

        # 如果邮箱已存在，阻止重复注册
        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册，请直接登录。')
            return redirect(url_for('auth.login'))

        # 对密码做哈希处理
        hashed_pw = generate_password_hash(password)

        # 新建 User 实例并赋值
        user =User()
        user.name = name
        user.phone_number = phone_number
        user.gender = gender
        user.email = email
        user.password_hash = hashed_pw
        user.id_card = id_card
        user.student_number = student_number
        user.verification_code = code
        user.code_sent_at=datetime.now()
        user.is_verified = False

        # 写入数据库
        db.session.add(user)
        db.session.commit()

        # 构造并发送邮件
        msg = Message(subject="[银行系统] 邮箱验证",recipients=[email])
        msg.body = f'您的验证码为：{code}，有效期 10 分钟。'
        mail.send(msg)

        flash('验证码已发送，请在下方输入。')
        # 跳转到验证码输入页，带上 user_id
        return redirect(url_for('auth.verify_email', user_id=user.id))

    # GET 请求渲染注册表单
    return render_template('register.html')


### 重发邮箱验证码 ###
@auth_bp.route('/resend_code/<int:user_id>', methods=['POST'])
def resend_code(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_verified:
        flash('邮箱已验证，无需重发。')
        return redirect(url_for('auth.login'))

    # 生成新码并更新
    code = generate_code()
    user.verification_code = code
    user.code_sent_at = datetime.now()
    db.session.commit()

    msg = Message("【银行系统】重发邮箱验证码", recipients=[user.email])
    msg.body = f"您的新验证码是：{code}，有效期10分钟。"
    mail.send(msg)

    flash('验证码已重发，请检查邮箱。')
    return redirect(url_for('auth.verify_email', user_id=user.id))


### 验证邮箱 ###
@auth_bp.route('/verify_email/<int:user_id>', methods=['GET', 'POST'])
def verify_email(user_id):
    user = User.query.get_or_404(user_id)
    # 判断验证码是否过期（10 分钟）
    expired = user.code_sent_at and (datetime.now() - user.code_sent_at > timedelta(minutes=10))

    if request.method == 'POST':
        input_code = request.form['code']
        if expired:
            flash('验证码已过期，请重发。')
        elif input_code == user.verification_code:
            user.is_verified = True
            user.verification_code = None
            user.code_sent_at = None
            db.session.commit()
            flash('邮箱验证成功，请登录。')
            return redirect(url_for('auth.login'))
        else:
            flash('验证码错误，请重试。')

    # 渲染验证码页面，并传入 user 与 expired 状态
    return render_template('verify_email.html', user=user, expired=expired)


### 登录：含锁定、失败计数、补发验证码 ###
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

        # 如果距离首次失败超过 1 天，重置计数
        now = datetime.now()
        if user.first_failed_at and now - user.first_failed_at > timedelta(days=1):
            user.failed_login_attempts = 0
            user.first_failed_at = None

        if check_password_hash(user.password_hash, password):
            # 密码对但邮箱未验证 → 重新发送验证码流程
            if not user.is_verified:

                code = generate_code()
                user.verification_code = code
                user.code_sent_at = datetime.now()
                db.session.commit()

                msg = Message(subject="[银行系统] 邮箱验证", recipients=[email])
                msg.body = f'您的验证码为：{code}，有效期 10 分钟。'
                mail.send(msg)

                flash('验证码已发送，请在下方输入。')
                return redirect(url_for('auth.verify_email', user_id=user.id))

            # 登录成功后重置失败计数
            user.failed_login_attempts = 0
            user.first_failed_at = None
            db.session.commit()

            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            # 密码错误 → 增加失败计数并可能锁定
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


### 登出 ###
@auth_bp.route('/logout')
def logout():
    from flask_login import logout_user
    logout_user()
    flash('已安全登出。')
    return redirect(url_for('auth.login'))


### 编辑个人信息（需登录） ###
@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        new_email = request.form['email']
        new_phone = request.form.get('phone')
        new_password = request.form.get('password')

        # 验证：若邮箱改动需检查唯一
        if new_email != current_user.email:
            if User.query.filter_by(email=new_email).first():
                flash('该邮箱已被占用，请换一个。')
                return redirect(url_for('auth.edit_profile'))
            current_user.email = new_email

        current_user.phone = new_phone

        # 密码非空则更新
        if new_password:
            current_user.password_hash = generate_password_hash(new_password)

        db.session.commit()
        flash('个人信息已更新。')
        return redirect(url_for('main.dashboard'))

    return render_template('edit_profile.html')


### 忘记密码：发送重置验证码 ###
@auth_bp.route('/forgot_password', methods=['GET','POST'])
def forgot_password():
    if request.method=='POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('该邮箱未注册。')
            return redirect(url_for('auth.forgot_password'))

        # 生成并发送重置验证码
        code = generate_code()
        user.reset_code = code
        user.reset_code_sent = datetime.now()
        db.session.commit()

        msg=Message("[银行系统] 密码重置验证码",
                    recipients=[email],
                    body=f"您的重置验证码：{code}，10分钟内有效。")
        mail.send(msg)
        flash('验证码已发送，请查收。')
        return redirect(url_for('auth.reset_password', user_id=user.id))
    return render_template('forgot_password.html')


### 重置密码 ###
@auth_bp.route('/reset_password/<int:user_id>', methods=['GET','POST'])
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    expired = user.reset_code_sent and (datetime.now()-user.reset_code_sent>timedelta(minutes=10))
    if request.method=='POST':
        code = request.form['code']
        new_pwd = request.form['password']
        if expired:
            flash('验证码已过期，请重新发送。')
        elif code!=user.reset_code:
            flash('验证码错误。')
        else:
            user.password_hash = generate_password_hash(new_pwd)
            user.reset_code = None
            user.reset_code_sent = None
            db.session.commit()
            flash('密码已重置，请登录。')
            return redirect(url_for('auth.login'))
    return render_template('reset_password.html', user=user, expired=expired)