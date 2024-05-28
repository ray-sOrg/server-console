#!/bin/bash

# 项目路径
PROJECT_DIR=/var/www/server/ray-flask

# 虚拟环境路径
VENV_DIR=$PROJECT_DIR/my_venv

# Gunicorn 配置文件路径
GUNICORN_CONF=$PROJECT_DIR/gunicorn_config.py

# 应用程序入口点
APP_MODULE=app:app

# 设置 FLASK_ENV 环境变量为 "production"
export FLASK_ENV=production

# 打印环境变量以确认设置正确
echo "FLASK_ENV is set to: $FLASK_ENV"

# 启动 Gunicorn 服务器
cd $PROJECT_DIR

# 激活虚拟环境
source $VENV_DIR/bin/activate

# 重新安装依赖项
pip install -r $PROJECT_DIR/requirements.txt

# 启动 Gunicorn 服务器
echo "Starting Gunicorn server..."
exec FLASK_ENV=production gunicorn -c $GUNICORN_CONF $APP_MODULE