from datetime import timedelta
import os

DIALECT = 'mysql'
DRIVER = 'pymysql'
USERNAME = 'root'
PASSWORD = 'Ttangtao123~'
HOST = '127.0.0.1'
PORT = '3306'
DATABASE = 'ray'
SQLALCHEMY_DATABASE_URI = "{}+{}://{}:{}@{}:{}/{}?charset=utf8".format(DIALECT, DRIVER, USERNAME, PASSWORD, HOST, PORT,
                                                                       DATABASE)
JWT_TOKEN_LOCATION = ["cookies"]
JWT_COOKIE_SECURE = False
JWT_SECRET_KEY = 'wjl'
JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_BROKER_URL = 'redis://localhost:6379/0'

# OSS 配置
access_key_id = 'LTAI5tQtaWvad7oobHnUZZqW'
access_key_secret = 'oWjbVLO9HRl0vZb1lsYxoHqWxjM0NF'
bucket_name = 'ray321'

IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production'
if IS_PRODUCTION:
    # 生产环境使用内网访问
    endpoint = 'oss-cn-chengdu-internal.aliyuncs.com'
else:
    # 本地开发使用外网访问
    endpoint = 'oss-cn-chengdu.aliyuncs.com'