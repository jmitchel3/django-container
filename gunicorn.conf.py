import multiprocessing

# Recommended: 2-4 workers per CPU core for Django
cpu_count = multiprocessing.cpu_count()
max_workers = 10
workers = min(cpu_count * 2 + 1, max_workers)

# Prevent stuck workers
timeout = 60
keepalive = 5

# Graceful handling
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"  # debug in prod is too verbose
errorlog = "-"
accesslog = "-"

# Custom access log format that includes host header
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" host="%({Host}i)s"'
)

# Performance
worker_class = "sync"  # Django works best with sync workers
preload_app = True
