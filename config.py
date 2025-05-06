import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///bank.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Mail 配置（SSL）
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))
    MAIL_USE_TLS = False  # 禁用 STARTTLS
    MAIL_USE_SSL = True  # 启用 SSL 直连
    MAIL_USERNAME = '480866948@qq.com'
    MAIL_PASSWORD = 'eqhsnyhpappvbhhf'
    MAIL_DEFAULT_SENDER = MAIL_USERNAME
    MAIL_DEBUG = True  # 开启邮件调试日志