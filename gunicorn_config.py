import multiprocessing

# 绑定的 IP 地址和端口号
bind = "127.0.0.1:5000"

# 工作进程数量（根据服务器的 CPU 核心数来调整）
workers = multiprocessing.cpu_count() * 2 + 1

# 每个工作进程的线程数
threads = 2

# 服务器日志文件路径
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"

# 设置日志记录级别
loglevel = "info"

# 是否在每次请求后重启工作进程
reload = True
