#!/usr/bin/env python3
"""
Скрипт для проверки локальной настройки
Проверяет работу Flask API и доступность статических файлов
"""

import requests
import os
import sys
from pathlib import Path

def check_flask_api():
    """Проверяет работу Flask API на localhost:5000"""
    print("=" * 60)
    print("1. Проверка Flask API (localhost:5000)")
    print("=" * 60)
    
    try:
        # Проверяем health endpoint или просто корень
        response = requests.get("http://localhost:5000/api/public/tariffs", timeout=5)
        if response.status_code in [200, 404]:  # 404 тоже нормально, если эндпоинта нет
            print("✓ Flask API доступен на http://localhost:5000")
            print(f"  Статус: {response.status_code}")
            return True
        else:
            print(f"✗ Flask API вернул неожиданный статус: {response.status_code}")
            return False
    except requests.ConnectionError:
        print("✗ Не удалось подключиться к Flask API")
        print("  Убедитесь, что Flask запущен: python app.py")
        return False
    except Exception as e:
        print(f"✗ Ошибка при проверке Flask API: {e}")
        return False

def check_build_files():
    """Проверяет наличие build файлов"""
    print("\n" + "=" * 60)
    print("2. Проверка build директории")
    print("=" * 60)
    
    build_path = Path("admin-panel/build")
    index_path = build_path / "index.html"
    
    if not build_path.exists():
        print(f"✗ Директория {build_path} не найдена")
        print("  Выполните: cd admin-panel && npm run build")
        return False
    
    if not index_path.exists():
        print(f"✗ Файл {index_path} не найден")
        print("  Выполните: cd admin-panel && npm run build")
        return False
    
    print(f"✓ Build директория найдена: {build_path}")
    print(f"✓ index.html найден: {index_path}")
    
    # Проверяем наличие основных файлов
    static_dir = build_path / "static"
    if static_dir.exists():
        js_files = list(static_dir.glob("js/*.js"))
        css_files = list(static_dir.glob("css/*.css"))
        print(f"✓ Найдено JS файлов: {len(js_files)}")
        print(f"✓ Найдено CSS файлов: {len(css_files)}")
    
    return True

def check_api_endpoints():
    """Проверяет несколько API эндпоинтов"""
    print("\n" + "=" * 60)
    print("3. Проверка API эндпоинтов")
    print("=" * 60)
    
    endpoints = [
        "/api/public/tariffs",
        "/api/public/tariff-features",
    ]
    
    base_url = "http://localhost:5000"
    results = []
    
    for endpoint in endpoints:
        try:
            url = base_url + endpoint
            response = requests.get(url, timeout=5)
            status = "✓" if response.status_code == 200 else "⚠"
            print(f"{status} {endpoint}: {response.status_code}")
            results.append(response.status_code == 200 or response.status_code == 404)
        except Exception as e:
            print(f"✗ {endpoint}: Ошибка - {e}")
            results.append(False)
    
    return all(results)

def start_test_server():
    """Предлагает запустить тестовый HTTP сервер"""
    print("\n" + "=" * 60)
    print("4. Запуск тестового HTTP сервера")
    print("=" * 60)
    
    build_path = Path("admin-panel/build").absolute()
    
    if not build_path.exists():
        print("✗ Build директория не найдена, пропускаем")
        return
    
    print(f"Для тестирования статических файлов выполните:")
    print(f"  cd {build_path}")
    print(f"  python -m http.server 8080")
    print(f"\nЗатем откройте в браузере: http://localhost:8080")
    print(f"\nИли используйте встроенный сервер Python:")
    print(f"  python -m http.server 8080 --directory {build_path}")

def main():
    print("\n" + "=" * 60)
    print("ПРОВЕРКА ЛОКАЛЬНОЙ НАСТРОЙКИ")
    print("=" * 60 + "\n")
    
    results = []
    
    # Проверка Flask
    results.append(check_flask_api())
    
    # Проверка build
    results.append(check_build_files())
    
    # Проверка API эндпоинтов
    if results[0]:  # Если Flask работает
        results.append(check_api_endpoints())
    
    # Инструкции по тестовому серверу
    start_test_server()
    
    # Итоги
    print("\n" + "=" * 60)
    print("ИТОГИ")
    print("=" * 60)
    
    if all(results):
        print("✓ Все проверки пройдены!")
        print("\nДля полного тестирования:")
        print("1. Убедитесь, что Flask запущен: python app.py")
        print("2. Запустите тестовый HTTP сервер для build (см. выше)")
        print("3. Откройте http://localhost:8080 в браузере")
        print("4. Проверьте работу API запросов в консоли браузера (F12)")
    else:
        print("✗ Некоторые проверки не пройдены")
        print("  Исправьте ошибки выше и запустите проверку снова")
    
    print("=" * 60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПроверка прервана пользователем")
        sys.exit(0)

