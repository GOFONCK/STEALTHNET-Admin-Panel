# Запуск Flask API через Gunicorn

## Установка Gunicorn

```bash
pip install gunicorn
```

Или добавьте в `requirements.txt`:
```
gunicorn>=21.2.0
```

## Запуск Flask API через Gunicorn

### Базовый запуск

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### С конфигурационным файлом

```bash
gunicorn -c gunicorn_config.py app:app
```

### С дополнительными параметрами

```bash
gunicorn \
  --workers 4 \
  --bind 0.0.0.0:5000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  app:app
```

## Параметры

- `-w, --workers` - количество воркеров (рекомендуется: 2 * CPU cores + 1)
- `-b, --bind` - адрес и порт для прослушивания
- `--timeout` - таймаут для воркеров (секунды)
- `--access-logfile` - файл для access логов (`-` = stdout)
- `--error-logfile` - файл для error логов (`-` = stdout)
- `--log-level` - уровень логирования (debug, info, warning, error, critical)
- `--reload` - автоматическая перезагрузка при изменении кода (только для разработки)

## Запуск как systemd сервис

1. Скопируйте `flask_api.service` в `/etc/systemd/system/`:

```bash
sudo cp flask_api.service /etc/systemd/system/
```

2. Отредактируйте пути в файле:

```bash
sudo nano /etc/systemd/system/flask_api.service
```

Измените:
- `WorkingDirectory=/path/to/your/api` → ваш путь к проекту
- `Environment="PATH=/path/to/your/venv/bin"` → путь к виртуальному окружению
- `ExecStart=/path/to/your/venv/bin/gunicorn` → полный путь к gunicorn

3. Перезагрузите systemd:

```bash
sudo systemctl daemon-reload
```

4. Запустите сервис:

```bash
sudo systemctl start flask_api
sudo systemctl enable flask_api  # автозапуск при загрузке
```

5. Проверьте статус:

```bash
sudo systemctl status flask_api
```

6. Просмотр логов:

```bash
sudo journalctl -u flask_api -f
```

## Запуск Telegram бота

**Важно:** Gunicorn НЕ подходит для Telegram бота, так как бот работает через polling, а не как WSGI приложение.

Для бота используйте systemd service:

1. Скопируйте `client_bot.service` в `/etc/systemd/system/`:

```bash
sudo cp client_bot.service /etc/systemd/system/
```

2. Отредактируйте пути:

```bash
sudo nano /etc/systemd/system/client_bot.service
```

3. Перезагрузите и запустите:

```bash
sudo systemctl daemon-reload
sudo systemctl start client_bot
sudo systemctl enable client_bot
```

4. Проверьте статус:

```bash
sudo systemctl status client_bot
```

5. Просмотр логов:

```bash
sudo journalctl -u client_bot -f
```

## Одновременный запуск обоих сервисов

```bash
# Flask API
sudo systemctl start flask_api
sudo systemctl enable flask_api

# Telegram бот
sudo systemctl start client_bot
sudo systemctl enable client_bot
```

## Проверка работы

### Flask API
```bash
curl http://localhost:5000/api/public/tariffs
```

### Telegram бот
Отправьте `/start` боту в Telegram

## Управление сервисами

```bash
# Остановить
sudo systemctl stop flask_api
sudo systemctl stop client_bot

# Перезапустить
sudo systemctl restart flask_api
sudo systemctl restart client_bot

# Статус
sudo systemctl status flask_api
sudo systemctl status client_bot

# Логи
sudo journalctl -u flask_api -n 50
sudo journalctl -u client_bot -n 50
```


