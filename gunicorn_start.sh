#!/bin/bash

# 项目路径
PROJECT_DIR=/var/www/server/ray-flask

# 虚拟环境路径
VENV_DIR=$PROJECT_DIR/my_venv

# Gunicorn 配置文件路径
GUNICORN_CONF=$PROJECT_DIR/gunicorn_config.py

# 应用程序入口点
APP_MODULE=app:app

# 启动 Gunicorn 服务器
cd $PROJECT_DIR
source $VENV_DIR/bin/activate
exec gunicorn -c $GUNICORN_CONF $APP_MODULE
