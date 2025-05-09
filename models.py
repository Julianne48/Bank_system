# models.py
from datetime import datetime
from extensions import db
from flask_login import UserMixin
import random


# 用户模型：存储用户基本信息、认证状态及与账户的关系
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)  # 存储哈希密码
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    reset_code = db.Column(db.String(6), nullable=True)
    reset_code_sent = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.BigInteger, default=lambda: int(datetime.now().timestamp() * 1000))

    @property
    def created_at_dt(self) -> datetime:
        return datetime.fromtimestamp(self.created_at / 1000.0)

    verification_code = db.Column(db.String(6), nullable=True)
    code_sent_at = db.Column(db.DateTime, nullable=True)
    name = db.Column(db.String(30), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    id_card = db.Column(db.String(18), nullable=True)
    phone_number = db.Column(db.String(11), nullable=True)
    student_number = db.Column(db.String(20), nullable=True)
    # 当天连续失败计数 & 首次失败时间
    is_locked = db.Column(db.Boolean, default=False)
    failed_login_attempts = db.Column(db.Integer, default=0)
    first_failed_at = db.Column(db.DateTime, nullable=True)
    # 一个用户可以拥有多个账户（User:Account = 1:N）
    accounts = db.relationship('Account', backref='user', lazy=True)


# 账户模型：存储账户信息及与交易的关系
class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bank_number = db.Column(db.String(16), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False, default="我的账户")
    balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 一个账户有多个交易记录（Account:Transaction = 1:N）
    transactions = db.relationship('Transaction', backref='account',lazy=True, foreign_keys='Transaction.account_id')


# 交易模型：记录存款、取款、转账等操作
class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    t_type = db.Column(db.String(20), nullable=False)  # 类型：Deposit, Withdraw, Transfer 等
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    other_account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'),nullable=True)
    other_account = db.relationship('Account',foreign_keys=[other_account_id],primaryjoin="Transaction.other_account_id==Account.id")


# 辅助函数：生成唯一银行卡号
def generate_bank_number():
    num = str(623000)
    for _ in range(10):
        num += str(random.randint(0, 9))
    return "".join(num)