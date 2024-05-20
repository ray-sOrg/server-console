from flask import Flask
from flask_cors import CORS
from extensions import db
from utils import register_api_blueprints
from flask_jwt_extended import JWTManager
import config

app = Flask(__name__)
CORS(app)
app.config.from_object(config)
app.config['JWT_SECRET_KEY'] = 'wjl'
jwt = JWTManager(app)
db.init_app(app)

# 创建应用程序上下文
with app.app_context():
    # 获取数据库中现有表的信息
    inspector = db.inspect(db.engine)
    # 检查并创建所有不存在的表
    if 'image' not in inspector.get_table_names() or 'user' not in inspector.get_table_names():
        db.create_all()


# 调用注册蓝图的方法
register_api_blueprints(app)


if __name__ == '__main__':
    app.run()
