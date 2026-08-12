from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from flask_cors import CORS
from extensions import db, jwt
from utils.register_api_blueprints import register_api_blueprints
from utils.db_utils import create_missing_tables
from utils.jwt_errors import register_jwt_errors
from mycelery import make_celery
import config

app = Flask(__name__)

# CORS 配置：支持跨域携带 Cookie
CORS(app, supports_credentials=True, origins=[
    "https://console.tt829.cn",
    "https://weight.tt829.cn",
    "http://localhost:5173",  # 本地开发
    "http://localhost:4173",  # 体重管理本地开发
])
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


@app.route('/health')
def health_check():
    """健康检查端点，用于 Kubernetes liveness/readiness probe"""
    return {'status': 'healthy', 'service': 'server-console'}, 200


if __name__ == '__main__':
    app.run()
