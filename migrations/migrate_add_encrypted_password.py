#!/usr/bin/env python3
"""
Миграция: Добавление поля encrypted_password в таблицу User
"""

import sqlite3
import os
import sys

def find_db():
    """Найти файл БД"""
    possible_paths = [
        'instance/stealthnet.db',
        'stealthnet.db',
        os.path.join(os.path.dirname(__file__), 'instance', 'stealthnet.db'),
        os.path.join(os.path.dirname(__file__), 'stealthnet.db')
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def main():
    db_path = find_db()
    if not db_path:
        print("❌ Файл БД не найден!")
        print("Ищите в:")
        for path in ['instance/stealthnet.db', 'stealthnet.db']:
            print(f"  - {path}")
        sys.exit(1)
    
    print(f"📁 Найден файл БД: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже поле
        cursor.execute("PRAGMA table_info(user)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'encrypted_password' in columns:
            print("✅ Поле encrypted_password уже существует")
            conn.close()
            return
        
        # Добавляем поле
        print("🔄 Добавляем поле encrypted_password...")
        cursor.execute("ALTER TABLE user ADD COLUMN encrypted_password TEXT")
        conn.commit()
        
        print("✅ Поле encrypted_password успешно добавлено!")
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка SQLite: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

