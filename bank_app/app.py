from flask import Flask
from flask_login import LoginManager
from config import Config
from extensions import db, mail
from extensions import migrate
import webbrowser
from threading import Timer

def create_app():
    flask_app = Flask(__name__)
    flask_app.config.from_object(Config)

    # 将扩展绑定到 app
    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    mail.init_app(flask_app)

    # 初始化登录管理
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(flask_app)

    from models import User
    # 用户加载回调
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 延迟导入蓝图，避免循环引用
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.admin import admin_bp

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(main_bp)
    flask_app.register_blueprint(admin_bp)

    return flask_app

app = create_app()

if __name__ == '__main__':
    def open_browser():
        webbrowser.open(f'http://127.0.0.1:5000/')

    Timer(1, open_browser).start()
    app.run(debug=True,use_reloader=False)