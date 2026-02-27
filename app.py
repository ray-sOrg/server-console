from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from flask_cors import CORS
from extensions import db, jwt
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, set_access_cookies
from utils.register_api_blueprints import register_api_blueprints
from utils.db_utils import create_missing_tables
from utils.jwt_errors import register_jwt_errors
from mycelery import make_celery
import config
from datetime import datetime
from datetime import timedelta
from datetime import timezone

app = Flask(__name__)

CORS(app)
app.config.from_object(config)

db.init_app(app)
jwt.init_app(app)


@app.after_request
def refresh_expiring_jwts(response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=5))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            set_access_cookies(response, access_token)
        return response
    except (RuntimeError, KeyError):
        # Case where there is not a valid JWT. Just return the original response
        return response


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
