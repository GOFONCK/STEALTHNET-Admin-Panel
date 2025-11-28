#!/bin/bash
# Скрипт для выполнения миграции на удаленном сервере
# Использование: ./migrate_add_badge_remote.sh

echo "=== Миграция базы данных: добавление поля badge ==="

# Путь к базе данных (измените на ваш путь)
DB_PATH="instance/stealthnet.db"

# Проверяем существование базы данных
if [ ! -f "$DB_PATH" ]; then
    echo "ОШИБКА: База данных $DB_PATH не найдена!"
    echo "Проверьте путь к базе данных в скрипте"
    exit 1
fi

# Выполняем миграцию через Python
python3 << EOF
import sqlite3
import os

DB_PATH = "$DB_PATH"

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Проверяем, существует ли колонка badge
    cursor.execute("PRAGMA table_info(tariff)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'badge' in columns:
        print("✓ Колонка 'badge' уже существует в таблице tariff")
    else:
        # Добавляем колонку badge
        cursor.execute("ALTER TABLE tariff ADD COLUMN badge VARCHAR(50)")
        conn.commit()
        print("✓ Колонка 'badge' успешно добавлена в таблицу tariff")
    
    conn.close()
    print("✓ Миграция завершена успешно!")
    
except Exception as e:
    print(f"✗ Ошибка при миграции: {e}")
    exit(1)
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "=== Миграция успешно завершена ==="
    echo "Теперь перезапустите Flask приложение"
else
    echo ""
    echo "=== Ошибка при выполнении миграции ==="
    exit 1
fi

