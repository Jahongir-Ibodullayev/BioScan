"""Production gunicorn config — gevent workers for high concurrency.

Default `gunicorn` (no flags) runs 1 sync worker, which serializes
requests one at a time. With gevent + 4 workers × 100 connections,
this VPS can handle ~400 concurrent slow requests.
"""
import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "127.0.0.1:8000")

# 2 × CPUs is the standard rule. Each gevent worker handles ~100
# concurrent connections via greenlets, so total concurrency is
# (workers × worker_connections).
workers = int(os.getenv("GUNICORN_WORKERS", str(multiprocessing.cpu_count() * 2)))
worker_class = "gevent"
worker_connections = 100

# Keep connections alive for 75s — matches Nginx upstream keepalive.
keepalive = 75
timeout = 60
graceful_timeout = 30

# Recycle workers periodically to avoid memory leaks.
max_requests = 2000
max_requests_jitter = 200

# Pre-load the app once in the master, then fork. Saves ~200 MB RSS
# across 8 workers and cuts cold-start time on every reload.
preload_app = True

# TZ §3.8 — Heartbeat fayllarini tmpfs'da saqlash, har request 5-10ms tejaymiz
worker_tmp_dir = "/dev/shm"

accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")

# Trust X-Forwarded-* from Nginx
forwarded_allow_ips = "*"
proxy_allow_ips = "*"
