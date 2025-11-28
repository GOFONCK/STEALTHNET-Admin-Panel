#!/usr/bin/env python3
"""
Скрипт для добавления поля promo_code_id в таблицу Payment
Запустите этот скрипт один раз после обновления кода
"""

import sqlite3
import os
import sys

def find_database_path():
    possible_paths = [
        'instance/stealthnet.db',
        'stealthnet.db',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'stealthnet.db'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stealthnet.db')
    ]
    
    # Если путь указан как аргумент командной строки
    if len(sys.argv) > 1:
        possible_paths.insert(0, sys.argv[1])

    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def migrate_database():
    db_path = find_database_path()

    if not db_path:
        print("Ошибка: База данных 'stealthnet.db' не найдена ни в одном из ожидаемых мест.")
        print("Пожалуйста, укажите путь к базе данных как аргумент: python3 migrate_add_promo_code_id.py /path/to/stealthnet.db")
        sys.exit(1)

    print(f"Попытка подключения к базе данных: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли таблица payment
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payment'")
        if not cursor.fetchone():
            print("Ошибка: Таблица 'payment' не найдена в базе данных.")
            conn.close()
            sys.exit(1)

        # Проверяем, существует ли уже колонка promo_code_id
        cursor.execute("PRAGMA table_info(payment)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'promo_code_id' in columns:
            print("Колонка 'promo_code_id' уже существует в таблице 'payment'. Миграция не требуется.")
        else:
            # Добавляем колонку promo_code_id
            cursor.execute("ALTER TABLE payment ADD COLUMN promo_code_id INTEGER")
            conn.commit()
            print("Колонка 'promo_code_id' успешно добавлена в таблицу 'payment'.")
        
        conn.close()
        print("Миграция завершена успешно!")
        
    except sqlite3.Error as e:
        print(f"Ошибка SQLite при миграции: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Неизвестная ошибка при миграции: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_database()

