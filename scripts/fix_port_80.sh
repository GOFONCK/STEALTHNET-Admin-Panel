#!/bin/bash
# Скрипт для диагностики и исправления проблемы с портом 80

echo "=========================================="
echo "ПРОВЕРКА ПРОЦЕССОВ НА ПОРТУ 80"
echo "=========================================="
echo ""

# Проверяем, что занимает порт 80
echo "1. Процессы, использующие порт 80:"
sudo lsof -i :80 || sudo netstat -tulpn | grep :80 || sudo ss -tulpn | grep :80
echo ""

echo "2. Статус nginx:"
sudo systemctl status nginx --no-pager | head -10
echo ""

echo "3. Статус apache (если установлен):"
sudo systemctl status apache2 --no-pager 2>/dev/null | head -10 || echo "Apache не установлен"
echo ""

echo "4. Статус caddy (если установлен):"
sudo systemctl status caddy --no-pager 2>/dev/null | head -10 || echo "Caddy не установлен"
echo ""

echo "=========================================="
echo "РЕШЕНИЕ:"
echo "=========================================="
echo ""
echo "Если Caddy занимает порт 80, временно остановите его:"
echo "  sudo systemctl stop caddy"
echo ""
echo "Затем запустите certbot:"
echo "  sudo certbot --nginx -d ad.trendbot.space"
echo ""
echo "После получения сертификата запустите Caddy обратно:"
echo "  sudo systemctl start caddy"
echo ""

