"""Production entrypoint: gunicorn -c gunicorn.conf.py run:app."""
import os
bind = "127.0.0.1:8000"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
worker_class = "gthread"
threads = 4
timeout = 30
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 100
preload_app = False
accesslog = "-"
errorlog = "-"
# %U excludes query strings so old emailed query tokens cannot enter access logs.
access_log_format = '%(h)s %(m)s %(U)s %(s)s %(L)s'
forwarded_allow_ips = "127.0.0.1"


def on_starting(server):
    if os.getenv("APP_ENV") != "production":
        raise RuntimeError("Configurar APP_ENV=production antes del despliegue")
