from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from api.upload_api import upload_pb
from api.index_api import index_pb
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
    # 检查表是否存在
    if 'image' not in inspector.get_table_names():
        # 如果不存在，则创建 Image 表
        db.create_all()


app.register_blueprint(index_pb, url_prefix='/api')

# 注册用户 API 蓝图
app.register_blueprint(upload_pb, url_prefix='/api')


if __name__ == '__main__':
    app.run()
