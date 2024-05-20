import os


def register_api_blueprints(app):
    api_dir = os.path.join(app.root_path, 'api')
    api_files = os.listdir(api_dir)

    for api_file in api_files:
        if api_file.endswith('_api.py'):
            module_name = os.path.splitext(api_file)[0]
            module = __import__(f'api.{module_name}', fromlist=[module_name])
            # 获取蓝图对象并注册
            blueprint = getattr(module, f'{module_name}_pb')
            app.register_blueprint(blueprint)

