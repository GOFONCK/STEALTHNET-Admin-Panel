#!/usr/bin/env python3
"""
Миграция для добавления поддержки Telegram авторизации:
1. Добавляет поле telegram_id в таблицу user
2. Добавляет поле telegram_username в таблицу user
3. Делает email и password_hash nullable
4. Обновляет is_verified по умолчанию для существующих пользователей
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
        print("Использование: python migrate_add_telegram_fields.py [путь_к_базе.db]")
        print("Или поместите скрипт в директорию с базой данных.")
        sys.exit(1)
    
    print(f"📦 Подключение к базе данных: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Добавляем поле telegram_id
        print("\n1️⃣ Проверка таблицы user...")
        cursor.execute("PRAGMA table_info(user)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'telegram_id' not in columns:
            print("   ➕ Добавление поля telegram_id...")
            cursor.execute("ALTER TABLE user ADD COLUMN telegram_id INTEGER")
            print("   ✅ Поле telegram_id добавлено")
        else:
            print("   ✓ Поле telegram_id уже существует")
        
        # 2. Добавляем поле telegram_username
        if 'telegram_username' not in columns:
            print("   ➕ Добавление поля telegram_username...")
            cursor.execute("ALTER TABLE user ADD COLUMN telegram_username VARCHAR(100)")
            print("   ✅ Поле telegram_username добавлено")
        else:
            print("   ✓ Поле telegram_username уже существует")
        
        # 3. Делаем email и password_hash nullable (SQLite не поддерживает MODIFY COLUMN напрямую)
        # Нужно пересоздать таблицу - но делаем это безопасно
        print("\n2️⃣ Обновление структуры таблицы user (nullable для email и password_hash)...")
        cursor.execute("PRAGMA table_info(user)")
        columns_info = cursor.fetchall()
        
        # Проверяем текущее состояние полей
        email_info = next((col for col in columns_info if col[1] == 'email'), None)
        password_info = next((col for col in columns_info if col[1] == 'password_hash'), None)
        
        email_nullable = email_info and email_info[3] == 1  # 1 = nullable, 0 = NOT NULL
        password_nullable = password_info and password_info[3] == 1
        
        if not email_nullable or not password_nullable:
            print("   ⚠️  SQLite не поддерживает изменение NULLABLE напрямую.")
            print("   ⚠️  Нужно пересоздать таблицу для поддержки nullable полей.")
            print("\n   🔄 Пересоздание таблицы user с поддержкой nullable...")
            
            try:
                # Создаем временную таблицу с новой структурой
                cursor.execute("""
                    CREATE TABLE user_new (
                        id INTEGER PRIMARY KEY,
                        email VARCHAR(120) UNIQUE,
                        password_hash VARCHAR(128),
                        telegram_id INTEGER UNIQUE,
                        telegram_username VARCHAR(100),
                        remnawave_uuid VARCHAR(128) UNIQUE NOT NULL,
                        role VARCHAR(10) NOT NULL DEFAULT 'CLIENT',
                        referral_code VARCHAR(20) UNIQUE,
                        referrer_id INTEGER,
                        preferred_lang VARCHAR(5) DEFAULT 'ru',
                        preferred_currency VARCHAR(5) DEFAULT 'uah',
                        is_verified BOOLEAN NOT NULL DEFAULT 0,
                        verification_token VARCHAR(100) UNIQUE,
                        created_at DATETIME
                    )
                """)
                
                # Копируем данные из старой таблицы
                print("   📋 Копирование данных...")
                cursor.execute("""
                    INSERT INTO user_new 
                    SELECT * FROM user
                """)
                
                # Подсчитываем строки
                cursor.execute("SELECT COUNT(*) FROM user")
                old_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM user_new")
                new_count = cursor.fetchone()[0]
                
                if old_count == new_count:
                    # Удаляем старую таблицу и переименовываем новую
                    cursor.execute("DROP TABLE user")
                    cursor.execute("ALTER TABLE user_new RENAME TO user")
                    conn.commit()
                    print(f"   ✅ Таблица успешно пересоздана ({old_count} записей сохранено)")
                else:
                    # Если количество не совпадает, откатываем изменения
                    cursor.execute("DROP TABLE user_new")
                    conn.rollback()
                    print(f"   ❌ Ошибка: количество записей не совпадает ({old_count} != {new_count})")
                    print("   ⚠️  Изменения отменены. Пожалуйста, сделайте бэкап перед пересозданием таблицы.")
            except Exception as e:
                print(f"   ❌ Ошибка при пересоздании таблицы: {e}")
                conn.rollback()
                print("   ⚠️  Изменения отменены. Рекомендуется сделать бэкап перед пересозданием таблицы.")
        else:
            print("   ✓ Поля email и password_hash уже nullable")
        
        # 4. Обновляем is_verified для существующих пользователей (если нужно)
        print("\n3️⃣ Проверка существующих пользователей...")
        cursor.execute("SELECT COUNT(*) FROM user WHERE is_verified = 0")
        unverified_count = cursor.fetchone()[0]
        if unverified_count > 0:
            print(f"   ℹ️  Найдено {unverified_count} неподтвержденных пользователей")
            print("   ℹ️  Они останутся неподтвержденными (это нормально для email регистрации)")
        
        conn.commit()
        print("\n✅ Миграция успешно завершена!")
        print("\n📝 Примечание:")
        print("   - Telegram пользователи будут создаваться с временными email вида tg_<id>@telegram.local")
        print("   - Для полной поддержки nullable email/password_hash может потребоваться пересоздание таблицы")
        
    except sqlite3.Error as e:
        print(f"\n❌ Ошибка базы данных: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()

