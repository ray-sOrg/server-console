import multiprocessing
import os

# 绑定的 IP 地址和端口号（容器环境使用 0.0.0.0）
bind = "0.0.0.0:5000"

# 工作进程数量
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# 每个工作进程的线程数
threads = int(os.getenv("GUNICORN_THREADS", 2))

# 日志输出到 stdout/stderr（容器环境最佳实践）
accesslog = "-"
errorlog = "-"

# 设置日志记录级别
loglevel = os.getenv("LOG_LEVEL", "info")

# 生产环境不自动重载
reload = False

# 超时时间
timeout = 120
keepalive = 5
