# Инструкция по миграции базы данных для добавления поля badge

## Вариант 1: Запуск скрипта миграции на сервере

1. Загрузите файл `migrate_add_badge.py` на ваш сервер (через FTP, SCP, или скопируйте содержимое)

2. Подключитесь к серверу по SSH

3. Перейдите в директорию с проектом:
   ```bash
   cd /path/to/your/project
   ```

4. Запустите скрипт миграции:
   ```bash
   python3 migrate_add_badge.py
   ```
   
   Или если используется виртуальное окружение:
   ```bash
   source venv/bin/activate  # или source env/bin/activate
   python migrate_add_badge.py
   ```

5. Проверьте результат - должно появиться сообщение:
   ```
   Колонка 'badge' успешно добавлена в таблицу tariff
   Миграция завершена успешно!
   ```

## Вариант 2: Выполнение SQL команды напрямую

Если у вас есть доступ к базе данных через SQL клиент или консоль:

1. Подключитесь к базе данных SQLite:
   ```bash
   sqlite3 instance/stealthnet.db
   ```
   
   Или если база в другом месте:
   ```bash
   sqlite3 /path/to/stealthnet.db
   ```

2. Выполните SQL команду:
   ```sql
   ALTER TABLE tariff ADD COLUMN badge VARCHAR(50);
   ```

3. Проверьте, что колонка добавлена:
   ```sql
   PRAGMA table_info(tariff);
   ```
   
   Должна появиться строка с `badge`

4. Выйдите из SQLite:
   ```sql
   .quit
   ```

## Вариант 3: Через Python консоль на сервере

1. Подключитесь к серверу по SSH

2. Перейдите в директорию проекта и активируйте виртуальное окружение (если есть)

3. Запустите Python:
   ```bash
   python3
   ```

4. Выполните команды:
   ```python
   import sqlite3
   import os
   
   DB_PATH = 'instance/stealthnet.db'  # или путь к вашей БД
   
   conn = sqlite3.connect(DB_PATH)
   cursor = conn.cursor()
   
   # Проверяем, существует ли колонка
   cursor.execute("PRAGMA table_info(tariff)")
   columns = [col[1] for col in cursor.fetchall()]
   
   if 'badge' in columns:
       print("Колонка 'badge' уже существует")
   else:
       cursor.execute("ALTER TABLE tariff ADD COLUMN badge VARCHAR(50)")
       conn.commit()
       print("Колонка 'badge' успешно добавлена")
   
   conn.close()
   ```

## Вариант 4: Если используется PostgreSQL или другая БД

Если у вас не SQLite, а PostgreSQL или другая БД, нужно использовать соответствующий SQL:

### PostgreSQL:
```sql
ALTER TABLE tariff ADD COLUMN badge VARCHAR(50);
```

### MySQL/MariaDB:
```sql
ALTER TABLE tariff ADD COLUMN badge VARCHAR(50) NULL;
```

## Проверка после миграции

После выполнения миграции проверьте:

1. Перезапустите Flask приложение
2. Откройте админ-панель
3. Отредактируйте тариф и добавьте бейдж
4. Перезагрузите страницу - бейдж должен сохраниться

## Важно!

- **Сделайте резервную копию базы данных** перед выполнением миграции
- Убедитесь, что Flask приложение **остановлено** во время миграции (или используйте транзакции)
- После миграции **перезапустите** Flask приложение

