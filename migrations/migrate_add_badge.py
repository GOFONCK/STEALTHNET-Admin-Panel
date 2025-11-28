#!/usr/bin/env python3
"""
Скрипт для добавления поля badge в таблицу Tariff
Запустите этот скрипт один раз после обновления кода

Использование:
    python3 migrate_add_badge.py
    или
    python migrate_add_badge.py

Скрипт автоматически найдет базу данных в стандартных местах:
- instance/stealthnet.db
- stealthnet.db
"""

import sqlite3
import os
import sys

def find_database():
    """Ищет базу данных в стандартных местах"""
    possible_paths = [
        'instance/stealthnet.db',
        'stealthnet.db',
        os.path.join(os.path.dirname(__file__), 'instance', 'stealthnet.db'),
        os.path.join(os.path.dirname(__file__), 'stealthnet.db'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return os.path.abspath(path)
    
    return None

def check_column_exists(cursor, table_name, column_name):
    """Проверяет, существует ли колонка в таблице"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    return column_name in columns

def migrate_database(db_path):
    """Выполняет миграцию базы данных"""
    if not os.path.exists(db_path):
        print(f"❌ ОШИБКА: База данных {db_path} не найдена!")
        print("\nВозможные пути к базе данных:")
        print("  - instance/stealthnet.db")
        print("  - stealthnet.db")
        print("\nУбедитесь, что вы запускаете скрипт из корневой директории проекта")
        return False
    
    try:
        print(f"📂 Подключение к базе данных: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли таблица tariff
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tariff'")
        if not cursor.fetchone():
            print("❌ ОШИБКА: Таблица 'tariff' не найдена в базе данных!")
            conn.close()
            return False
        
        # Проверяем, существует ли уже колонка badge
        if check_column_exists(cursor, 'tariff', 'badge'):
            print("✓ Колонка 'badge' уже существует в таблице tariff")
            conn.close()
            return True
        
        # Добавляем колонку badge
        print("🔄 Добавление колонки 'badge' в таблицу 'tariff'...")
        cursor.execute("ALTER TABLE tariff ADD COLUMN badge VARCHAR(50)")
        conn.commit()
        
        # Проверяем, что колонка добавлена
        if check_column_exists(cursor, 'badge', 'badge'):
            print("✓ Колонка 'badge' успешно добавлена в таблицу tariff")
        else:
            print("⚠️  ВНИМАНИЕ: Колонка добавлена, но проверка не прошла")
        
        conn.close()
        print("✅ Миграция завершена успешно!")
        print("\n📝 Следующие шаги:")
        print("  1. Перезапустите Flask приложение")
        print("  2. Проверьте работу бейджей в админ-панели")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ ОШИБКА SQLite: {e}")
        return False
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        return False

def main():
    """Главная функция"""
    print("=" * 60)
    print("  Миграция базы данных: добавление поля 'badge'")
    print("=" * 60)
    print()
    
    # Ищем базу данных
    db_path = find_database()
    
    if not db_path:
        print("❌ База данных не найдена!")
        print("\nПопробуйте указать путь вручную:")
        print("  python3 migrate_add_badge.py /path/to/stealthnet.db")
        print()
        
        # Пробуем получить путь из аргументов командной строки
        if len(sys.argv) > 1:
            db_path = sys.argv[1]
            if not os.path.exists(db_path):
                print(f"❌ Указанный путь не существует: {db_path}")
                sys.exit(1)
        else:
            sys.exit(1)
    
    # Выполняем миграцию
    success = migrate_database(db_path)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
