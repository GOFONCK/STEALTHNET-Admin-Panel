# Конфигурация Gunicorn для Flask API
import multiprocessing
import os

# Количество воркеров (рекомендуется: 2 * CPU cores + 1)
workers = multiprocessing.cpu_count() * 2 + 1

# Класс воркера
worker_class = "sync"

# Таймауты
timeout = 120
keepalive = 5

# Логирование
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# Имя приложения
wsgi_app = "app:app"

# Биндинг
bind = "0.0.0.0:5000"

# Перезагрузка при изменении кода (только для разработки)
reload = False

# Максимальное количество запросов на воркер перед перезапуском
max_requests = 1000
max_requests_jitter = 50

# Предзагрузка приложения
preload_app = True

# Обработка сигналов
graceful_timeout = 30

