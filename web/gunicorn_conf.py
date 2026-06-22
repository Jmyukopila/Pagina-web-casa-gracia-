"""
Gunicorn config for production. Uses async Uvicorn workers so a single
container handles many simultaneous connections without blocking.

Scale further by running several replicas behind Nginx (see docker-compose).
"""
import multiprocessing
import os

# Bind inside the container; Nginx proxies to it.
bind = os.getenv("BIND", "0.0.0.0:8000")

# (2 x cores) + 1 is a good default. Override with WEB_CONCURRENCY.
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"

# Recycle workers periodically to avoid memory creep; jitter avoids thundering herd.
max_requests = 1200
max_requests_jitter = 200

timeout = 30
graceful_timeout = 30
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
