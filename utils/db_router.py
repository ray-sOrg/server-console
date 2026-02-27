# 数据库路由工具
# 根据 URL 前缀切换不同的数据库连接

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import request
import config

# 创建多个引擎
engines = {
    'restaurant': create_engine(
        config.DATABASE_RESTAURANT,
        pool_pre_ping=True,
        pool_recycle=300
    ),
    'default': create_engine(
        config.DATABASE_DEFAULT,
        pool_pre_ping=True,
        pool_recycle=300
    )
}

# 创建一个 session factory
def get_session(db_name='default'):
    """获取指定数据库的 session"""
    engine = engines.get(db_name, engines['default'])
    session_factory = sessionmaker(bind=engine)
    return scoped_session(session_factory)


def get_db_from_url():
    """
    根据 URL 路径判断使用哪个数据库
    /api/chuan-dai/* → restaurant (餐馆数据库)
    其他 → default (综合数据库)
    """
    path = request.path
    
    if '/chuan-dai/' in path or path.startswith('/chuan-dai'):
        return 'restaurant'
    
    return 'default'


def get_db_session():
    """根据 URL 自动选择数据库"""
    db_name = get_db_from_url()
    return get_session(db_name)
