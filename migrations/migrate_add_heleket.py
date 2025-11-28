#!/usr/bin/env python3
"""
Миграция для добавления поддержки Heleket платежной системы:
1. Добавляет поле heleket_api_key в таблицу payment_setting
2. Добавляет поле payment_provider в таблицу payment
"""

import sqlite3
import os
import sys

def find_db():
    """Ищет базу данных в стандартных местах"""
    possible_paths = [
        'instance/stealthnet.db',
        'stealthnet.db',
        '../instance/stealthnet.db',
        '../stealthnet.db'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def main():
    # Получаем путь к БД из аргументов или ищем автоматически
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not db_path:
        db_path = find_db()
    
    if not db_path:
        print("❌ База данных не найдена!")
        print("Использование: python migrate_add_heleket.py [путь_к_базе.db]")
        print("Или поместите скрипт в директорию с базой данных.")
        sys.exit(1)
    
    print(f"📦 Подключение к базе данных: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Добавляем поле heleket_api_key в payment_setting
        print("\n1️⃣ Проверка таблицы payment_setting...")
        cursor.execute("PRAGMA table_info(payment_setting)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'heleket_api_key' not in columns:
            print("   ➕ Добавление поля heleket_api_key...")
            cursor.execute("ALTER TABLE payment_setting ADD COLUMN heleket_api_key TEXT")
            print("   ✅ Поле heleket_api_key добавлено")
        else:
            print("   ✓ Поле heleket_api_key уже существует")
        
        # 2. Добавляем поле payment_provider в payment
        print("\n2️⃣ Проверка таблицы payment...")
        cursor.execute("PRAGMA table_info(payment)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'payment_provider' not in columns:
            print("   ➕ Добавление поля payment_provider...")
            cursor.execute("ALTER TABLE payment ADD COLUMN payment_provider VARCHAR(20) DEFAULT 'crystalpay'")
            print("   ✅ Поле payment_provider добавлено")
        else:
            print("   ✓ Поле payment_provider уже существует")
        
        conn.commit()
        print("\n✅ Миграция успешно завершена!")
        
    except sqlite3.Error as e:
        print(f"\n❌ Ошибка базы данных: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()

