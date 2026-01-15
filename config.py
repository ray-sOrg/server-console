from datetime import timedelta
import os

DIALECT = 'mysql'
DRIVER = 'pymysql'
USERNAME = os.getenv('DB_USERNAME', 'root')
PASSWORD = os.getenv('DB_PASSWORD', '')
HOST = os.getenv('DB_HOST', '127.0.0.1')
PORT = os.getenv('DB_PORT', '3306')
DATABASE = os.getenv('DB_NAME', 'ray')
SQLALCHEMY_DATABASE_URI = "{}+{}://{}:{}@{}:{}/{}?charset=utf8".format(DIALECT, DRIVER, USERNAME, PASSWORD, HOST, PORT,
                                                                       DATABASE)
JWT_TOKEN_LOCATION = ["cookies"]
JWT_COOKIE_SECURE = False
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-this-to-a-strong-secret-key')
JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_BROKER_URL = 'redis://localhost:6379/0'

# OSS 配置 - 从环境变量读取
access_key_id = os.getenv('OSS_ACCESS_KEY_ID', '')
access_key_secret = os.getenv('OSS_ACCESS_KEY_SECRET', '')
bucket_name = os.getenv('OSS_BUCKET_NAME', 'ray321')

IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production'
if IS_PRODUCTION:
    # 生产环境使用内网访问
    endpoint = 'oss-cn-chengdu-internal.aliyuncs.com'
else:
    # 本地开发使用外网访问
    endpoint = 'oss-cn-chengdu.aliyuncs.com'
