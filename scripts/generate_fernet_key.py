#!/usr/bin/env python3
"""
Скрипт для генерации FERNET_KEY
FERNET_KEY используется для шифрования данных в приложении.
"""

from cryptography.fernet import Fernet

def generate_fernet_key():
    """Генерирует новый FERNET_KEY"""
    key = Fernet.generate_key()
    key_str = key.decode('utf-8')
    
    print("=" * 60)
    print("Сгенерированный FERNET_KEY:")
    print("=" * 60)
    print(key_str)
    print("=" * 60)
    print("\nДобавьте эту строку в ваш .env файл:")
    print(f"FERNET_KEY={key_str}")
    print("=" * 60)
    
    return key_str

if __name__ == "__main__":
    generate_fernet_key()

