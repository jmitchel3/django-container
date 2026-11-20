# Gunicorn reads WEB_CONCURRENCY and defaults to one worker.

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

# Log the request path without query strings or referrers, which can carry tokens.
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(m)s %(U)s %(H)s" %(s)s %(b)s "%(a)s" host="%({host}i)s"'
)

# Performance
worker_class = "sync"  # Django works best with sync workers
preload_app = True
