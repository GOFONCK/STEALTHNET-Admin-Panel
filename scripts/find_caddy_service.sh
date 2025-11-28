#!/bin/bash
# Скрипт для поиска способа запуска Caddy

echo "Проверка способа запуска Caddy:"
echo ""

echo "1. Systemd units:"
systemctl list-units --all | grep -i caddy
echo ""

echo "2. Systemd service files:"
ls -la /etc/systemd/system/ | grep -i caddy
ls -la /lib/systemd/system/ | grep -i caddy
echo ""

echo "3. Crontab:"
crontab -l 2>/dev/null | grep -i caddy || echo "Нет в crontab"
echo ""

echo "4. Init scripts:"
ls -la /etc/init.d/ | grep -i caddy || echo "Нет в init.d"
echo ""

echo "5. Supervisor:"
ls -la /etc/supervisor/conf.d/ 2>/dev/null | grep -i caddy || echo "Нет в supervisor"
echo ""

echo "6. Проверка родительского процесса:"
ps -ef | grep caddy | grep -v grep
echo ""

echo "7. Проверка systemd status:"
systemctl status caddy 2>&1 | head -20





