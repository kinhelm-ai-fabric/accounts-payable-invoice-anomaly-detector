import multiprocessing
import os

bind = "0.0.0.0:" + os.environ.get("PORT", "5000")
workers = int(os.environ.get("WEB_CONCURRENCY", min(multiprocessing.cpu_count() + 1, 4)))
worker_class = "sync"
timeout = int(os.environ.get("APP_GUNICORN_TIMEOUT", "120"))
preload_app = True  # REQUIRED: single create_app() call, shared SECRET_KEY
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
