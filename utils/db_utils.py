from extensions import db
import importlib
import os
import logging


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


def create_missing_tables(app):
    import_models()  # 确保模型已导入
    with app.app_context():
        try:
            # 获取数据库中现有表的信息
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            print(f'________{existing_tables}')
            # 检查并创建所有不存在的表
            if 'image' not in existing_tables or 'user' not in existing_tables:
                print(f'________缺失表')
                db.create_all()
            else:
                print('________所有表已存在')
        except Exception as e:
            logging.error(f'Error creating tables: {e}')
