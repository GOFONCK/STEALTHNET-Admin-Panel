#!/bin/bash
# Скрипт для полного удаления Caddy

echo "=========================================="
echo "УДАЛЕНИЕ CADDY"
echo "=========================================="
echo ""

# 1. Остановить все процессы Caddy
echo "1. Остановка процессов Caddy..."
pkill -9 caddy
sleep 2

# 2. Проверить, что процессы остановлены
echo "2. Проверка процессов..."
ps aux | grep caddy | grep -v grep || echo "✓ Процессы Caddy остановлены"
echo ""

# 3. Удалить systemd service (если есть)
echo "3. Удаление systemd service..."
systemctl stop caddy 2>/dev/null
systemctl disable caddy 2>/dev/null
rm -f /etc/systemd/system/caddy.service
rm -f /etc/systemd/system/caddy@.service
rm -f /lib/systemd/system/caddy.service
systemctl daemon-reload
echo "✓ Systemd service удален"
echo ""

# 4. Удалить бинарный файл
echo "4. Удаление бинарного файла..."
rm -f /usr/bin/caddy
rm -f /usr/local/bin/caddy
echo "✓ Бинарный файл удален"
echo ""

# 5. Удалить конфигурационные файлы
echo "5. Удаление конфигурационных файлов..."
rm -rf /etc/caddy
echo "✓ Конфигурационные файлы удалены"
echo ""

# 6. Удалить данные и кэш
echo "6. Удаление данных и кэша..."
rm -rf ~/.local/share/caddy
rm -rf /var/lib/caddy
rm -rf /opt/caddy
echo "✓ Данные и кэш удалены"
echo ""

# 7. Удалить логи
echo "7. Удаление логов..."
rm -rf /var/log/caddy
echo "✓ Логи удалены"
echo ""

# 8. Проверить, что порт 80 свободен
echo "8. Проверка порта 80..."
netstat -tulpn | grep :80 || echo "✓ Порт 80 свободен"
echo ""

echo "=========================================="
echo "CADDY УДАЛЕН"
echo "=========================================="
echo ""
echo "Теперь вы можете:"
echo "1. Запустить certbot: sudo certbot --nginx -d ad.trendbot.space"
echo "2. Или проверить, что порт 80 свободен: sudo netstat -tulpn | grep :80"
echo ""





