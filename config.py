from datetime import timedelta
import os

# Supabase PostgreSQL 配置
# Supabase 连接格式: postgresql://postgres:[password]@[host]:[port]/[database]
SQLALCHEMY_DATABASE_URI = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:password@localhost:5432/postgres'
)

JWT_TOKEN_LOCATION = ["cookies"]
JWT_COOKIE_SECURE = False
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-this-to-a-strong-secret-key')
JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

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
