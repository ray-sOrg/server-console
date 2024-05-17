from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from api.upload_api import upload_pb
from api.index_api import index_pb
from api.user_api import user_pb
from extensions import db
import config

app = Flask(__name__)
CORS(app)
app.config.from_object(config)
db.init_app(app)

# 创建应用程序上下文
with app.app_context():
    # 获取数据库中现有表的信息
    inspector = db.inspect(db.engine)
    # 检查并创建所有不存在的表
    if 'image' not in inspector.get_table_names() or 'user' not in inspector.get_table_names():
        db.create_all()


# 注册用户 API 蓝图
app.register_blueprint(index_pb)
app.register_blueprint(upload_pb)
app.register_blueprint(user_pb)


if __name__ == '__main__':
    app.run()
