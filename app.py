from flask import Flask
from flask_cors import CORS
from extensions import db, jwt
from utils.register_api_blueprints import register_api_blueprints
from utils.db_utils import create_missing_tables
from utils.jwt_errors import register_jwt_errors
import config
import os
import logging


app = Flask(__name__)

logging.basicConfig(filename='flask_env.log', level=logging.DEBUG)  # 将日志记录到文件中，设置日志级别为 DEBUG

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


# 获取 FLASK_ENV 的值
flask_env = os.environ.get('FLASK_ENV')
app.logger.debug(f"FLASK_ENV: {flask_env}")


if __name__ == '__main__':
    app.run()
