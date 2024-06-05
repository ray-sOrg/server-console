from flask import Flask
from flask_cors import CORS
from extensions import db, jwt
from utils.register_api_blueprints import register_api_blueprints
from utils.db_utils import create_missing_tables
from utils.jwt_errors import register_jwt_errors
from dotenv import load_dotenv
from mycelery import make_celery
import config

load_dotenv()

app = Flask(__name__)

CORS(app)
app.config.from_object(config)

db.init_app(app)
jwt.init_app(app)


# 注册 JWT 错误处理程序
register_jwt_errors()

# 确保在 create_all() 之前导入模型并检查缺失表
create_missing_tables(app)

# 调用注册蓝图的方法
register_api_blueprints(app)

# 构建celery
celery = make_celery(app)

if __name__ == '__main__':
    app.run()
