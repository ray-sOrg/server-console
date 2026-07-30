# =================== Single Stage Build ===================
FROM python:3.11-slim

WORKDIR /app

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --index-url "$PIP_INDEX_URL" -r requirements.txt

# 复制应用代码并设置权限
COPY --chown=appuser:appuser . .

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# 使用 Gunicorn 启动应用
CMD ["gunicorn", "-c", "gunicorn_config.py", "app:app"]
