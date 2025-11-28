#!/bin/bash
# Скрипт для проверки работы через curl

echo "=========================================="
echo "ПРОВЕРКА FLASK API (localhost:5000)"
echo "=========================================="
echo ""

# 1. Проверка доступности Flask
echo "1. Проверка доступности Flask API:"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:5000/api/public/tariffs
echo ""

# 2. Проверка эндпоинта тарифов
echo "2. Проверка /api/public/tariffs:"
curl -X GET http://localhost:5000/api/public/tariffs \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | head -20
echo ""

# 3. Проверка эндпоинта функций тарифов
echo "3. Проверка /api/public/tariff-features:"
curl -X GET http://localhost:5000/api/public/tariff-features \
  -H "Content-Type: application/json" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | head -20
echo ""

# 4. Проверка CORS заголовков
echo "4. Проверка CORS заголовков:"
curl -X GET http://localhost:5000/api/public/tariffs \
  -H "Origin: http://localhost:8080" \
  -H "Content-Type: application/json" \
  -v 2>&1 | grep -i "access-control"
echo ""

echo "=========================================="
echo "ПРОВЕРКА СТАТИЧЕСКИХ ФАЙЛОВ"
echo "=========================================="
echo ""

# 5. Проверка index.html (если запущен тестовый сервер на 8080)
echo "5. Проверка index.html (если запущен сервер на 8080):"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:8080/ || echo "Сервер на порту 8080 не запущен"
echo ""

echo "=========================================="
echo "ИТОГИ"
echo "=========================================="
echo ""
echo "Если все статусы 200 - все работает!"
echo ""
echo "Для запуска тестового сервера статики:"
echo "  cd admin-panel/build"
echo "  python -m http.server 8080"
echo ""

