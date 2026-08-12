from datetime import timedelta
import os

IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production'

# ========================================
# 多数据库配置
# 敏感信息从环境变量读取，不要硬编码！
# ========================================

# 餐馆系统数据库 (portal-chuan-dai-h5)
# 示例: postgresql://postgres.xxx:password@host:5432/postgres
DATABASE_RESTAURANT = os.getenv('DATABASE_URL_RESTAURANT', '')

# 综合后台数据库 (婚礼、照片等) - 默认数据库
# 示例: postgresql://postgres.xxx:password@host:5432/postgres
DATABASE_DEFAULT = os.getenv('DATABASE_URL', '')

# 如果没有配置数据库，使用默认的本地 PostgreSQL
if not DATABASE_DEFAULT:
    DATABASE_DEFAULT = 'postgresql://postgres:password@localhost:5432/postgres'

SQLALCHEMY_DATABASE_URI = DATABASE_DEFAULT

# 处理 Supabase PgBouncer 连接
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_pre_ping': True,
    # Supabase's pooler already manages server-side connections. Recycling every
    # five minutes caused user-facing writes to pay the full TLS/database cold
    # connection cost, which can exceed ten seconds from this region.
    'pool_recycle': 1800,
    'pool_size': 2,
    'max_overflow': 2,
    'pool_timeout': 20,
}

# JWT 配置
JWT_TOKEN_LOCATION = ["cookies"]
JWT_COOKIE_SECURE = IS_PRODUCTION
JWT_COOKIE_DOMAIN = os.getenv('JWT_COOKIE_DOMAIN') or ('.tt829.cn' if IS_PRODUCTION else None)
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'change-this-to-a-strong-secret-key')
JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=180)
JWT_SESSION_COOKIE = False
JWT_COOKIE_SAMESITE = 'Lax'
# The refresh JWT is only needed by authentication endpoints. Its readable
# CSRF companion remains on / so the SPA can send the double-submit header.
JWT_REFRESH_COOKIE_PATH = '/api/auth'
JWT_REFRESH_CSRF_COOKIE_PATH = '/'

# Celery 配置
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# OSS 配置 - 从环境变量读取
access_key_id = os.getenv('OSS_ACCESS_KEY_ID', '')
access_key_secret = os.getenv('OSS_ACCESS_KEY_SECRET', '')
bucket_name = os.getenv('OSS_BUCKET_NAME', 'ray321')

if IS_PRODUCTION:
    endpoint = 'oss-cn-chengdu-internal.aliyuncs.com'
else:
    endpoint = 'oss-cn-chengdu.aliyuncs.com'
