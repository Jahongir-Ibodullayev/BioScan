"""Gunicorn + Uvicorn workers — production deployment.

Async I/O bilan ko'p workerga ehtiyoj yo'q — har bir worker minglab concurrent
so'rov bajara oladi (event loop). Worker soni = CPU yadrolar soni.
"""
import multiprocessing
import os

bind = os.environ.get("BIND", "127.0.0.1:8001")
# Async: CPU yadrolar = workerlar (Django'da 2N+1 sinxron edi)
workers = int(os.environ.get("WEB_CONCURRENCY", max(2, multiprocessing.cpu_count())))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = int(os.environ.get("TIMEOUT", "120"))
keepalive = 65  # browser keepalive bilan teng
graceful_timeout = 30
max_requests = 5000
max_requests_jitter = 500
loglevel = os.environ.get("LOG_LEVEL", "info")
accesslog = "-"
errorlog = "-"
# Worker process'ni nomlash — `ps aux | grep gunicorn`da ko'rinadi
proc_name = "bioscan-fastapi"
# Server socketga 2048 ulanish kutadi
backlog = 2048
