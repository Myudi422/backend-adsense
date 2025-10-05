# Gunicorn configuration file for AdSense API Backend
# Kompatibel dengan Unicorn-style deployment

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Application
wsgi_app = "app:app"

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "adsense_api_backend"

# Server mechanics
daemon = False
pidfile = "/tmp/adsense_api_backend.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment if needed)
# keyfile = "path/to/keyfile"
# certfile = "path/to/certfile"

# Preload app for better performance
preload_app = True

# Enable stats
enable_stdio_inheritance = True