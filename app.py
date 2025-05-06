from flask import Flask
from flask_login import LoginManager
from config import Config
from extensions import db, mail
from extensions import migrate

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 将扩展绑定到 app
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # 初始化登录管理
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from models import User
    # 用户加载回调
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 延迟导入蓝图，避免循环引用
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    return app

# 全局 app 实例
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)