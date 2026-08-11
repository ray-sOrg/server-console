import importlib
import logging
import os

from sqlalchemy import inspect, text

from extensions import db


REQUIRED_COLUMNS = {
    'app_user': {
        'display_name': 'VARCHAR(100)',
        'height_cm': 'INTEGER',
        'birth_date': 'DATE',
    },
    'fitness_session': {
        'readiness_score': 'SMALLINT',
        'effort_score': 'SMALLINT',
        'pain_flag': 'BOOLEAN NOT NULL DEFAULT FALSE',
        'pain_notes': 'TEXT',
    },
}


def get_model_modules():
    # 获取当前脚本所在目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取 model 目录的绝对路径
    models_path = os.path.join(current_dir, '..', 'model')

    if not os.path.exists(models_path):
        raise FileNotFoundError(f"Models directory does not exist: {models_path}")

    # 获取所有 .py 文件（不包括 __init__.py）
    model_files = [f[:-3] for f in os.listdir(models_path) if f.endswith('.py') and f != '__init__.py']
    return model_files


def import_models():
    model_files = get_model_modules()
    for model_file in model_files:
        module_name = f'model.{model_file}'
        importlib.import_module(module_name)


def add_missing_columns():
    """Apply small, additive schema upgrades needed by existing installations."""
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())

    with db.engine.begin() as connection:
        for table_name, required_columns in REQUIRED_COLUMNS.items():
            if table_name not in existing_tables:
                continue

            existing_columns = {
                column['name'] for column in inspector.get_columns(table_name)
            }
            for column_name, column_type in required_columns.items():
                if column_name in existing_columns:
                    continue

                connection.execute(text(
                    f'ALTER TABLE {table_name} '
                    f'ADD COLUMN {column_name} {column_type}'
                ))
                logging.info(
                    'Added missing database column %s.%s',
                    table_name,
                    column_name,
                )


def create_missing_tables(app):
    import_models()  # 确保模型已导入
    with app.app_context():
        try:
            # 获取数据库中现有表的信息
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            print(f'获取数据库中现有表的信息________{existing_tables}')

            # 获取models目录下的所有.py文件名
            project_root = os.path.dirname(os.path.dirname(__file__))  # 获取根目录
            model_dir = os.path.join(project_root, 'model')

            required_tables = [
                os.path.splitext(f)[0]
                for f in os.listdir(model_dir)
                if f.endswith('.py') and not f.startswith('__')
            ]
            print(f'获取所有model中应有表的信息________{required_tables}')

            # 检查是否有任意一个需要的表不存在
            missing_tables = [table for table in required_tables if table not in existing_tables]

            # 检查并创建所有不存在的表
            if missing_tables:
                print(f'________缺失表')
                db.create_all()
            else:
                print('________所有表已存在')

            add_missing_columns()
        except Exception as e:
            logging.error(f'Error creating tables: {e}')
