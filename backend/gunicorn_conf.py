# gunicorn configuration for SEARCH_Goods
import multiprocessing

workers = max(2, multiprocessing.cpu_count() * 2)
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 30
keepalive = 2
bind = "0.0.0.0:8000"
proc_name = "search_goods_gunicorn"
accesslog = "-"  # stdout
errorlog = "-"   # stdout
loglevel = "info"
