# =================== Stage 1: Builder ===================
FROM python:3.11-slim AS builder

WORKDIR /app

# 复制 requirements.txt
COPY requirements.txt .

# 安装 Python 依赖到临时目录
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# =================== Stage 2: Runtime ===================
FROM python:3.11-slim AS runner

WORKDIR /app

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

# 从 builder 阶段复制已安装的包到系统路径
COPY --from=builder /install /usr/local

# 确保 PATH 包含可执行文件路径
ENV PATH=/usr/local/bin:$PATH

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
