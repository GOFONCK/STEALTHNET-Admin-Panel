#!/usr/bin/env python3
"""
Telegram Bot для клиентов StealthNET VPN
Предоставляет функционал Dashboard через Telegram интерфейс
"""

import os
import logging
import requests
import asyncio
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
CLIENT_BOT_TOKEN = os.getenv("CLIENT_BOT_TOKEN")  # Токен бота для клиентов
FLASK_API_URL = os.getenv("FLASK_API_URL", "http://localhost:5000")  # URL Flask API
MINIAPP_URL = os.getenv("MINIAPP_URL", "https://panel.stealthnet.app")  # URL для miniapp


def escape_markdown_v2(text: str) -> str:
    """Экранирует специальные символы для MarkdownV2"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def has_cards(text: str) -> bool:
    """Проверяет, содержит ли текст карточки (╔═══╗)"""
    return '╔' in text or '║' in text or '╚' in text


def clean_markdown_for_cards(text: str) -> str:
    """Убирает Markdown-форматирование из текста с карточками"""
    # Убираем ** для жирного текста, но оставляем структуру
    result = text.replace('**', '')
    # Убираем ` для моноширинного текста
    result = result.replace('`', '')
    return result


def format_card(title: str, content: str, icon: str = "📋") -> str:
    """Форматирует красивую карточку в современном стиле"""
    return f"{icon} **{title}**\n{content}\n"


def format_info_line(label: str, value: str, icon: str = "") -> str:
    """Форматирует информационную строку"""
    if icon:
        return f"{icon} {label}: {value}\n"
    return f"{label}: {value}\n"

if not CLIENT_BOT_TOKEN:
    raise ValueError("CLIENT_BOT_TOKEN не установлен в переменных окружения!")

# Проверка URL для miniapp (должен быть HTTPS)
if MINIAPP_URL and not MINIAPP_URL.startswith("https://"):
    logger.warning(f"MINIAPP_URL должен начинаться с https://, текущее значение: {MINIAPP_URL}")


class ClientBotAPI:
    """Класс для взаимодействия с Flask API"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[dict]:
        """Получить пользователя по Telegram ID через API бота или создать JWT"""
        # Сначала пытаемся получить JWT токен через telegram-login эндпоинт
        # Но для бота нам нужен другой подход - создадим специальный эндпоинт
        # Пока используем прямой запрос к БД через Flask API
        
        # Временное решение: используем внутренний эндпоинт для ботов
        try:
            response = self.session.post(
                f"{self.api_url}/api/bot/get-token",
                json={"telegram_id": telegram_id},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("token")
        except Exception as e:
            logger.error(f"Ошибка получения токена: {e}")
        
        return None
    
    def register_user(self, telegram_id: int, telegram_username: str = "", ref_code: str = None, preferred_lang: str = None, preferred_currency: str = None) -> Optional[dict]:
        """Зарегистрировать пользователя через бота"""
        try:
            payload = {
                "telegram_id": telegram_id,
                "telegram_username": telegram_username,
                "ref_code": ref_code
            }
            if preferred_lang:
                payload["preferred_lang"] = preferred_lang
            if preferred_currency:
                payload["preferred_currency"] = preferred_currency
            
            response = self.session.post(
                f"{self.api_url}/api/bot/register",
                json=payload,
                timeout=30
            )
            if response.status_code == 201:
                return response.json()
            elif response.status_code == 400:
                # Пользователь уже зарегистрирован
                return response.json()
        except Exception as e:
            logger.error(f"Ошибка регистрации: {e}")
        return None
    
    def get_credentials(self, telegram_id: int) -> Optional[dict]:
        """Получить логин (email) и пароль пользователя для входа на сайте"""
        try:
            response = self.session.post(
                f"{self.api_url}/api/bot/get-credentials",
                json={"telegram_id": telegram_id},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Ошибка получения credentials: {e}")
        return None
    
    def get_user_data(self, token: str, force_refresh: bool = False) -> Optional[dict]:
        """Получить данные пользователя"""
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            # Добавляем timestamp для предотвращения кэширования
            url = f"{self.api_url}/api/client/me"
            if force_refresh:
                url += f"?_t={int(datetime.now().timestamp() * 1000)}"
            
            response = self.session.get(
                url,
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                user_data = data.get("response") or data
                # Логируем для отладки
                if user_data:
                    logger.debug(f"User data keys: {list(user_data.keys())[:15]}")
                    logger.debug(f"User preferred_lang: {user_data.get('preferred_lang')}, preferred_currency: {user_data.get('preferred_currency')}")
                return user_data
        except Exception as e:
            logger.error(f"Ошибка получения данных пользователя: {e}")
        return None
    
    def get_tariffs(self) -> list:
        """Получить список тарифов"""
        try:
            response = self.session.get(
                f"{self.api_url}/api/public/tariffs",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Ошибка получения тарифов: {e}")
        return []
    
    def get_available_payment_methods(self) -> list:
        """Получить список доступных способов оплаты"""
        try:
            response = self.session.get(
                f"{self.api_url}/api/public/available-payment-methods",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("available_methods", [])
        except Exception as e:
            logger.error(f"Ошибка получения способов оплаты: {e}")
        return []
    
    def get_nodes(self, token: str) -> list:
        """Получить список серверов"""
        try:
            response = self.session.get(
                f"{self.api_url}/api/client/nodes",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response", {}).get("activeNodes", [])
        except Exception as e:
            logger.error(f"Ошибка получения серверов: {e}")
        return []
    
    def activate_trial(self, token: str) -> dict:
        """Активировать триал"""
        try:
            response = self.session.post(
                f"{self.api_url}/api/client/activate-trial",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Ошибка активации триала: {e}")
        return {"success": False, "message": "Ошибка активации триала"}
    
    def create_payment(self, token: str, tariff_id: int, payment_provider: str, promo_code: Optional[str] = None) -> dict:
        """Создать платеж"""
        try:
            payload = {
                "tariff_id": tariff_id,
                "payment_provider": payment_provider,
                "promo_code": promo_code
            }
            response = self.session.post(
                f"{self.api_url}/api/client/create-payment",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Ошибка создания платежа: {e}")
        return {"success": False, "message": "Ошибка создания платежа"}
    
    def get_support_tickets(self, token: str) -> list:
        """Получить список тикетов поддержки"""
        try:
            response = self.session.get(
                f"{self.api_url}/api/client/support-tickets",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Ошибка получения тикетов: {e}")
        return []
    
    def create_support_ticket(self, token: str, subject: str, message: str) -> dict:
        """Создать тикет поддержки"""
        try:
            response = self.session.post(
                f"{self.api_url}/api/client/support-tickets",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"subject": subject, "message": message},
                timeout=10
            )
            # API возвращает 201 при создании
            if response.status_code in [200, 201]:
                return response.json()
        except Exception as e:
            logger.error(f"Ошибка создания тикета: {e}")
        return {"success": False, "message": "Ошибка создания тикета"}
    
    def get_ticket_messages(self, token: str, ticket_id: int) -> dict:
        """Получить сообщения тикета"""
        try:
            response = self.session.get(
                f"{self.api_url}/api/support-tickets/{ticket_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Ошибка получения сообщений тикета: {e}")
        return {}
    
    def save_settings(self, token: str, lang: Optional[str] = None, currency: Optional[str] = None) -> dict:
        """Сохранить настройки пользователя (язык, валюта)"""
        try:
            payload = {}
            if lang:
                payload["lang"] = lang
            if currency:
                payload["currency"] = currency
            
            if not payload:
                return {"success": False, "message": "Нет данных для сохранения"}
            
            logger.info(f"Saving settings: {payload}")
            response = self.session.post(
                f"{self.api_url}/api/client/settings",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
                timeout=10
            )
            logger.info(f"Settings save response: {response.status_code}, {response.text}")
            if response.status_code == 200:
                return {"success": True, "message": "Настройки сохранены"}
            else:
                logger.error(f"Failed to save settings: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {e}")
        return {"success": False, "message": "Ошибка сохранения настроек"}
    
    def reply_to_ticket(self, token: str, ticket_id: int, message: str) -> dict:
        """Ответить на тикет"""
        try:
            response = self.session.post(
                f"{self.api_url}/api/support-tickets/{ticket_id}/reply",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"message": message},
                timeout=10
            )
            if response.status_code in [200, 201]:
                return response.json()
        except Exception as e:
            logger.error(f"Ошибка ответа на тикет: {e}")
        return {"success": False, "message": "Ошибка ответа на тикет"}


# Инициализация API клиента
api = ClientBotAPI(FLASK_API_URL)

# Кэш токенов пользователей (в продакшене лучше использовать Redis)
user_tokens = {}

# Словари переводов для разных языков
TRANSLATIONS = {
    'ru': {
        'main_menu': 'Главное меню',
        'subscription_status': 'Статус подписки',
        'tariffs': 'Тарифы',
        'servers': 'Серверы',
        'referrals': 'Рефералы',
        'support': 'Поддержка',
        'settings': '⚙️ Настройки',
        'currency': 'Валюта',
        'language': 'Язык',
        'select_currency': 'Выберите валюту:',
        'select_language': 'Выберите язык:',
        'settings_saved': '✅ Настройки сохранены',
        'back': '🔙 Назад',
        'welcome': 'Добро пожаловать',
        'subscription_active': 'Активна',
        'subscription_inactive': 'Не активна',
        'expires': 'Истекает',
        'days_left': 'Осталось дней',
        'traffic': 'Трафик',
        'unlimited': 'Безлимитный',
        'used': 'Использовано',
        'login_data': 'Данные для входа',
        'email': 'Логин',
        'password': 'Пароль',
        'connect': 'Подключиться',
        'activate_trial': 'Активировать триал',
        'select_tariff': 'Выбрать тариф',
        'price': 'Цена',
        'duration': 'Длительность',
        'days': 'дней',
        'select_payment': 'Выберите способ оплаты',
        'payment_created': 'Платеж создан',
        'go_to_payment': 'Перейти к оплате',
        'referral_program': 'Реферальная программа',
        'your_referral_link': 'Ваша реферальная ссылка',
        'your_code': 'Ваш код',
        'copy_link': 'Копировать ссылку',
        'link_copied': 'Ссылка отправлена в чат',
        'support_tickets': 'Ваши тикеты',
        'create_ticket': 'Создать тикет',
        'ticket_created': 'Тикет создан',
        'ticket_number': 'Номер тикета',
        'subject': 'Тема',
        'reply': 'Ответить',
        'reply_sent': 'Ответ отправлен',
        'servers_list': 'Список серверов',
        'online': 'Онлайн',
        'offline': 'Офлайн',
        'not_registered': 'Вы еще не зарегистрированы',
        'register': 'Зарегистрироваться',
        'register_success': 'Регистрация успешна',
        'trial_activated': 'Триал активирован',
        'trial_days': 'Вы получили 3 дня премиум доступа',
        'error': 'Ошибка',
        'auth_error': 'Ошибка авторизации',
        'not_found': 'Не найдено',
        'loading': 'Загрузка...',
        'welcome_bot': 'Добро пожаловать в StealthNET VPN Bot!',
        'not_registered_text': 'Вы еще не зарегистрированы в системе.',
        'register_here': 'Вы можете зарегистрироваться прямо здесь в боте или на сайте.',
        'after_register': 'После регистрации вы получите логин и пароль для входа на сайте.',
        'welcome_user': 'Добро пожаловать',
        'stealthnet_bot': 'StealthNET VPN Bot',
        'subscription_status_title': 'Статус подписки',
        'active': 'Активна',
        'inactive': 'Не активна',
        'expires_at': 'Истекает',
        'days_remaining': 'Осталось дней',
        'traffic_title': 'Трафик',
        'unlimited_traffic': 'Безлимитный',
        'traffic_used': 'Использовано',
        'login_data_title': 'Данные для входа на сайте',
        'login_label': 'Логин',
        'password_label': 'Пароль',
        'password_set': 'Установлен (недоступен)',
        'password_not_set': 'Пароль не установлен',
        'data_not_found': 'Данные не найдены',
        'connect_button': 'Подключиться',
        'activate_trial_button': 'Активировать триал',
        'select_tariff_button': 'Выбрать тариф',
        'main_menu_button': 'Главное меню',
        'status_button': 'Статус подписки',
        'tariffs_button': 'Тарифы',
        'servers_button': 'Серверы',
        'referrals_button': 'Рефералы',
        'support_button': 'Поддержка',
        'settings_button': 'Настройки',
        'cabinet_button': 'Кабинет',
        'subscription_link': 'Ссылка подключения',
        'traffic_usage': 'Использование трафика',
        'unlimited_traffic_full': 'Безлимитный трафик',
        'use_login_password': 'Используйте этот логин и пароль для входа на сайте',
        'select_tariff_type': 'Выберите тип тарифа',
        'basic_tier': 'Базовый',
        'pro_tier': 'Премиум',
        'elite_tier': 'Элитный',
        'from_price': 'От',
        'available_options': 'Доступно вариантов',
        'select_duration': 'Выберите длительность подписки',
        'per_day': 'день',
        'back_to_type': 'К выбору типа',
        'servers_title': 'Серверы',
        'available_servers': 'Доступные серверы',
        'total_servers': 'Всего серверов',
        'and_more': 'и еще',
        'servers_not_found': 'Серверы не найдены',
        'subscription_not_active': 'Подписка не активна. Активируйте триал или выберите тариф',
        'referral_program_title': 'Реферальная программа',
        'invite_friends': 'Приглашайте друзей и получайте бонусы!',
        'your_referral_code': 'Ваш код',
        'referral_code_not_found': 'Реферальный код не найден',
        'support_title': 'Поддержка',
        'your_tickets': 'Ваши тикеты',
        'no_tickets': 'У вас пока нет тикетов.',
        'select_action': 'Выберите действие',
        'create_ticket_button': 'Создать тикет',
        'ticket': 'Тикет',
        'ticket_created_success': 'Тикет создан!',
        'ticket_number_label': 'Номер тикета',
        'we_will_reply': 'Мы ответим вам в ближайшее время.',
        'view_ticket_support': 'Вы можете просмотреть тикет в разделе поддержки.',
        'reply_sent_success': 'Ответ отправлен!',
        'your_reply_added': 'Ваш ответ был добавлен в тикет.',
        'tariff_selected': 'Выбран тариф',
        'price_label': 'Цена',
        'duration_label': 'Длительность',
        'payment_methods': 'Выберите способ оплаты',
        'no_payment_methods': 'Нет доступных способов оплаты. Обратитесь в поддержку.',
        'back_to_tariffs': 'Назад к тарифам',
        'payment_created_title': 'Платеж создан',
        'go_to_payment_text': 'Перейдите по ссылке для оплаты:',
        'after_payment': 'После успешной оплаты подписка будет активирована автоматически.',
        'go_to_payment_button': 'Перейти к оплате',
        'trial_activated_title': 'Триал активирован!',
        'trial_days_received': 'Вы получили 3 дня премиум доступа.',
        'enjoy_vpn': 'Наслаждайтесь VPN без ограничений!',
        'registration_success': 'Регистрация успешна!',
        'your_login_data': 'Ваши данные для входа на сайте',
        'important_save': 'ВАЖНО: Сохраните эти данные! Пароль больше не будет показан.',
        'login_site': 'Войти на сайте',
        'now_use_bot': 'Теперь вы можете использовать все функции бота!',
        'already_registered': 'Вы уже зарегистрированы!',
        'registering': 'Регистрируем...',
        'registration_error': 'Ошибка регистрации',
        'registration_failed': 'Не удалось зарегистрироваться. Попробуйте позже или зарегистрируйтесь на сайте:',
        'ticket_view_title': 'Тикет',
        'status_label': 'Статус',
        'subject_label': 'Тема',
        'messages_label': 'Сообщения',
        'you': 'Вы',
        'support_label': 'Поддержка',
        'reply_button': 'Ответить',
        'back_to_support': 'К поддержке',
        'creating_ticket': 'Создание тикета',
        'send_subject': 'Отправьте тему тикета в следующем сообщении:',
        'subject_saved': 'Тема сохранена. Теперь отправьте текст сообщения:',
        'reply_to_ticket': 'Ответ на тикет',
        'send_reply': 'Отправьте ваш ответ в следующем сообщении:',
        'currency_changed': 'Валюта изменена',
        'language_changed': 'Язык изменен',
        'currency_already_selected': 'Эта валюта уже выбрана',
        'language_already_selected': 'Этот язык уже выбран',
        'invalid_currency': 'Неверная валюта',
        'invalid_language': 'Неверный язык',
        'failed_to_load': 'Не удалось загрузить данные',
        'failed_to_load_user': 'Не удалось загрузить данные пользователя',
        'tariffs_not_found': 'Тарифы не найдены',
        'tariff_not_found': 'Тариф не найден',
        'invalid_tariff_id': 'Ошибка: неверный ID тарифа',
        'link_sent_to_chat': 'Ссылка отправлена в чат',
        'click_to_copy': 'Нажмите на ссылку выше, чтобы скопировать её.',
        'click_link_to_copy': 'Нажмите на ссылку выше, чтобы скопировать её.',
        'send_ticket_subject': 'Отправьте тему тикета в следующем сообщении',
        'send_your_reply': 'Отправьте ваш ответ в следующем сообщении',
        'invalid_ticket_id': 'Ошибка: неверный ID тикета',
        'ticket_not_found': 'Не удалось загрузить тикет',
        'ticket_not_exists': 'Возможно, тикет не существует или у вас нет доступа.',
        'loading_ticket': 'Загружаем тикет...',
        'unknown': 'Неизвестно',
        'error_loading': 'Ошибка',
        'on_site': 'на сайте',
        'or': 'или',
        'activating_trial': 'Активируем триал',
        'error_activating_trial': 'Ошибка активации триала',
        'failed_activate_trial': 'Не удалось активировать триал. Попробуйте позже.',
        'creating_payment': 'Создаем платеж',
        'error_creating_payment': 'Ошибка создания платежа',
    },
    'ua': {
        'main_menu': 'Головне меню',
        'subscription_status': 'Статус підписки',
        'tariffs': 'Тарифи',
        'servers': 'Сервери',
        'referrals': 'Реферали',
        'support': 'Підтримка',
        'settings': '⚙️ Налаштування',
        'currency': 'Валюта',
        'language': 'Мова',
        'select_currency': 'Виберіть валюту:',
        'select_language': 'Виберіть мову:',
        'settings_saved': '✅ Налаштування збережено',
        'back': '🔙 Назад',
        'welcome': 'Ласкаво просимо',
        'subscription_active': 'Активна',
        'subscription_inactive': 'Не активна',
        'expires': 'Закінчується',
        'days_left': 'Залишилось днів',
        'traffic': 'Трафік',
        'unlimited': 'Безлімітний',
        'used': 'Використано',
        'login_data': 'Дані для входу',
        'email': 'Логін',
        'password': 'Пароль',
        'connect': 'Підключитися',
        'activate_trial': 'Активувати триал',
        'select_tariff': 'Вибрати тариф',
        'price': 'Ціна',
        'duration': 'Тривалість',
        'days': 'днів',
        'select_payment': 'Виберіть спосіб оплати',
        'payment_created': 'Платіж створено',
        'go_to_payment': 'Перейти до оплати',
        'referral_program': 'Реферальна програма',
        'your_referral_link': 'Ваша реферальна посилання',
        'your_code': 'Ваш код',
        'copy_link': 'Скопіювати посилання',
        'link_copied': 'Посилання відправлено в чат',
        'support_tickets': 'Ваші тікети',
        'create_ticket': 'Створити тікет',
        'ticket_created': 'Тікет створено',
        'ticket_number': 'Номер тікета',
        'subject': 'Тема',
        'reply': 'Відповісти',
        'reply_sent': 'Відповідь відправлено',
        'servers_list': 'Список серверів',
        'online': 'Онлайн',
        'offline': 'Офлайн',
        'not_registered': 'Ви ще не зареєстровані',
        'register': 'Зареєструватися',
        'register_success': 'Реєстрація успішна',
        'trial_activated': 'Триал активовано',
        'trial_days': 'Ви отримали 3 дні преміум доступу',
        'error': 'Помилка',
        'auth_error': 'Помилка авторизації',
        'not_found': 'Не знайдено',
        'loading': 'Завантаження...',
        'welcome_bot': 'Ласкаво просимо в StealthNET VPN Bot!',
        'not_registered_text': 'Ви ще не зареєстровані в системі.',
        'register_here': 'Ви можете зареєструватися прямо тут в боті або на сайті.',
        'after_register': 'Після реєстрації ви отримаєте логін і пароль для входу на сайті.',
        'welcome_user': 'Ласкаво просимо',
        'stealthnet_bot': 'StealthNET VPN Bot',
        'subscription_status_title': 'Статус підписки',
        'active': 'Активна',
        'inactive': 'Не активна',
        'expires_at': 'Закінчується',
        'days_remaining': 'Залишилось днів',
        'traffic_title': 'Трафік',
        'unlimited_traffic': 'Безлімітний',
        'traffic_used': 'Використано',
        'login_data_title': 'Дані для входу на сайті',
        'login_label': 'Логін',
        'password_label': 'Пароль',
        'password_set': 'Встановлено (недоступно)',
        'password_not_set': 'Пароль не встановлено',
        'data_not_found': 'Дані не знайдено',
        'connect_button': 'Підключитися',
        'activate_trial_button': 'Активувати триал',
        'select_tariff_button': 'Вибрати тариф',
        'main_menu_button': 'Головне меню',
        'status_button': 'Статус підписки',
        'tariffs_button': 'Тарифи',
        'servers_button': 'Сервери',
        'referrals_button': 'Реферали',
        'support_button': 'Підтримка',
        'settings_button': 'Налаштування',
        'cabinet_button': 'Кабінет',
        'subscription_link': 'Посилання підключення',
        'traffic_usage': 'Використання трафіку',
        'unlimited_traffic_full': 'Безлімітний трафік',
        'use_login_password': 'Використовуйте цей логін і пароль для входу на сайті',
        'select_tariff_type': 'Виберіть тип тарифу',
        'basic_tier': 'Базовий',
        'pro_tier': 'Преміум',
        'elite_tier': 'Елітний',
        'from_price': 'Від',
        'available_options': 'Доступно варіантів',
        'select_duration': 'Виберіть тривалість підписки',
        'per_day': 'день',
        'back_to_type': 'До вибору типу',
        'servers_title': 'Сервери',
        'available_servers': 'Доступні сервери',
        'total_servers': 'Всього серверів',
        'and_more': 'і ще',
        'servers_not_found': 'Сервери не знайдено',
        'subscription_not_active': 'Підписка не активна. Активуйте триал або виберіть тариф',
        'referral_program_title': 'Реферальна програма',
        'invite_friends': 'Запрошуйте друзів і отримуйте бонуси!',
        'your_referral_code': 'Ваш код',
        'referral_code_not_found': 'Реферальний код не знайдено',
        'support_title': 'Підтримка',
        'your_tickets': 'Ваші тікети',
        'no_tickets': 'У вас поки немає тікетів.',
        'select_action': 'Виберіть дію',
        'create_ticket_button': 'Створити тікет',
        'ticket': 'Тікет',
        'ticket_created_success': 'Тікет створено!',
        'ticket_number_label': 'Номер тікета',
        'we_will_reply': 'Ми відповімо вам найближчим часом.',
        'view_ticket_support': 'Ви можете переглянути тікет в розділі підтримки.',
        'reply_sent_success': 'Відповідь відправлено!',
        'your_reply_added': 'Ваша відповідь була додана в тікет.',
        'tariff_selected': 'Вибрано тариф',
        'price_label': 'Ціна',
        'duration_label': 'Тривалість',
        'payment_methods': 'Виберіть спосіб оплати',
        'no_payment_methods': 'Немає доступних способів оплати. Зверніться в підтримку.',
        'back_to_tariffs': 'Назад до тарифів',
        'payment_created_title': 'Платіж створено',
        'go_to_payment_text': 'Перейдіть за посиланням для оплати:',
        'after_payment': 'Після успішної оплати підписка буде активована автоматично.',
        'go_to_payment_button': 'Перейти до оплати',
        'trial_activated_title': 'Триал активовано!',
        'trial_days_received': 'Ви отримали 3 дні преміум доступу.',
        'enjoy_vpn': 'Насолоджуйтесь VPN без обмежень!',
        'registration_success': 'Реєстрація успішна!',
        'your_login_data': 'Ваші дані для входу на сайті',
        'important_save': 'ВАЖЛИВО: Збережіть ці дані! Пароль більше не буде показано.',
        'login_site': 'Увійти на сайті',
        'now_use_bot': 'Тепер ви можете використовувати всі функції бота!',
        'already_registered': 'Ви вже зареєстровані!',
        'registering': 'Реєструємо...',
        'registration_error': 'Помилка реєстрації',
        'registration_failed': 'Не вдалося зареєструватися. Спробуйте пізніше або зареєструйтеся на сайті:',
        'ticket_view_title': 'Тікет',
        'status_label': 'Статус',
        'subject_label': 'Тема',
        'messages_label': 'Повідомлення',
        'you': 'Ви',
        'support_label': 'Підтримка',
        'reply_button': 'Відповісти',
        'back_to_support': 'До підтримки',
        'creating_ticket': 'Створення тікета',
        'send_subject': 'Відправте тему тікета в наступному повідомленні:',
        'subject_saved': 'Тема збережена. Тепер відправте текст повідомлення:',
        'reply_to_ticket': 'Відповідь на тікет',
        'send_reply': 'Відправте вашу відповідь в наступному повідомленні:',
        'currency_changed': 'Валюта змінена',
        'language_changed': 'Мова змінена',
        'currency_already_selected': 'Ця валюта вже вибрана',
        'language_already_selected': 'Ця мова вже вибрана',
        'invalid_currency': 'Невірна валюта',
        'invalid_language': 'Невірна мова',
        'failed_to_load': 'Не вдалося завантажити дані',
        'failed_to_load_user': 'Не вдалося завантажити дані користувача',
        'tariffs_not_found': 'Тарифи не знайдено',
        'tariff_not_found': 'Тариф не знайдено',
        'invalid_tariff_id': 'Помилка: невірний ID тарифу',
        'link_sent_to_chat': 'Посилання відправлено в чат',
        'click_to_copy': 'Натисніть на посилання вище, щоб скопіювати його.',
        'click_link_to_copy': 'Натисніть на посилання вище, щоб скопіювати його.',
        'send_ticket_subject': 'Відправте тему тікета в наступному повідомленні',
        'send_your_reply': 'Відправте вашу відповідь в наступному повідомленні',
        'invalid_ticket_id': 'Помилка: невірний ID тікета',
        'ticket_not_found': 'Не вдалося завантажити тікет',
        'ticket_not_exists': 'Можливо, тікет не існує або у вас немає доступу.',
        'loading_ticket': 'Завантажуємо тікет...',
        'unknown': 'Невідомо',
        'error_loading': 'Помилка',
        'on_site': 'на сайті',
        'or': 'або',
        'activating_trial': 'Активуємо триал',
        'error_activating_trial': 'Помилка активації триалу',
        'failed_activate_trial': 'Не вдалося активувати триал. Спробуйте пізніше.',
        'creating_payment': 'Створюємо платіж',
        'error_creating_payment': 'Помилка створення платежу',
    },
    'en': {
        'main_menu': 'Main Menu',
        'subscription_status': 'Subscription Status',
        'tariffs': 'Tariffs',
        'servers': 'Servers',
        'referrals': 'Referrals',
        'support': 'Support',
        'settings': '⚙️ Settings',
        'currency': 'Currency',
        'language': 'Language',
        'select_currency': 'Select currency:',
        'select_language': 'Select language:',
        'settings_saved': '✅ Settings saved',
        'back': '🔙 Back',
        'welcome': 'Welcome',
        'subscription_active': 'Active',
        'subscription_inactive': 'Inactive',
        'expires': 'Expires',
        'days_left': 'Days left',
        'traffic': 'Traffic',
        'unlimited': 'Unlimited',
        'used': 'Used',
        'login_data': 'Login Data',
        'email': 'Email',
        'password': 'Password',
        'connect': 'Connect',
        'activate_trial': 'Activate Trial',
        'select_tariff': 'Select Tariff',
        'price': 'Price',
        'duration': 'Duration',
        'days': 'days',
        'select_payment': 'Select payment method',
        'payment_created': 'Payment created',
        'go_to_payment': 'Go to payment',
        'referral_program': 'Referral Program',
        'your_referral_link': 'Your referral link',
        'your_code': 'Your code',
        'copy_link': 'Copy link',
        'link_copied': 'Link sent to chat',
        'support_tickets': 'Your tickets',
        'create_ticket': 'Create ticket',
        'ticket_created': 'Ticket created',
        'ticket_number': 'Ticket number',
        'subject': 'Subject',
        'reply': 'Reply',
        'reply_sent': 'Reply sent',
        'servers_list': 'Servers list',
        'online': 'Online',
        'offline': 'Offline',
        'not_registered': 'You are not registered yet',
        'register': 'Register',
        'register_success': 'Registration successful',
        'trial_activated': 'Trial activated',
        'trial_days': 'You received 3 days of premium access',
        'error': 'Error',
        'auth_error': 'Authorization error',
        'not_found': 'Not found',
        'loading': 'Loading...',
        'welcome_bot': 'Welcome to StealthNET VPN Bot!',
        'not_registered_text': 'You are not registered in the system yet.',
        'register_here': 'You can register right here in the bot or on the website.',
        'after_register': 'After registration, you will receive login and password to access the website.',
        'welcome_user': 'Welcome',
        'stealthnet_bot': 'StealthNET VPN Bot',
        'subscription_status_title': 'Subscription Status',
        'active': 'Active',
        'inactive': 'Inactive',
        'expires_at': 'Expires',
        'days_remaining': 'Days remaining',
        'traffic_title': 'Traffic',
        'unlimited_traffic': 'Unlimited',
        'traffic_used': 'Used',
        'login_data_title': 'Login Data for Website',
        'login_label': 'Login',
        'password_label': 'Password',
        'password_set': 'Set (unavailable)',
        'password_not_set': 'Password not set',
        'data_not_found': 'Data not found',
        'connect_button': 'Connect',
        'activate_trial_button': 'Activate Trial',
        'select_tariff_button': 'Select Tariff',
        'main_menu_button': 'Main Menu',
        'status_button': 'Subscription Status',
        'tariffs_button': 'Tariffs',
        'servers_button': 'Servers',
        'referrals_button': 'Referrals',
        'support_button': 'Support',
        'settings_button': 'Settings',
        'cabinet_button': 'Cabinet',
        'subscription_link': 'Connection Link',
        'traffic_usage': 'Traffic Usage',
        'unlimited_traffic_full': 'Unlimited Traffic',
        'use_login_password': 'Use this login and password to access the website',
        'select_tariff_type': 'Select Tariff Type',
        'basic_tier': 'Basic',
        'pro_tier': 'Premium',
        'elite_tier': 'Elite',
        'from_price': 'From',
        'available_options': 'Available options',
        'select_duration': 'Select subscription duration',
        'per_day': 'day',
        'back_to_type': 'Back to Type Selection',
        'servers_title': 'Servers',
        'available_servers': 'Available Servers',
        'total_servers': 'Total Servers',
        'and_more': 'and more',
        'servers_not_found': 'Servers not found',
        'subscription_not_active': 'Subscription is not active. Activate trial or select a tariff',
        'referral_program_title': 'Referral Program',
        'invite_friends': 'Invite friends and get bonuses!',
        'your_referral_code': 'Your Code',
        'referral_code_not_found': 'Referral code not found',
        'support_title': 'Support',
        'your_tickets': 'Your Tickets',
        'no_tickets': 'You have no tickets yet.',
        'select_action': 'Select Action',
        'create_ticket_button': 'Create Ticket',
        'ticket': 'Ticket',
        'ticket_created_success': 'Ticket Created!',
        'ticket_number_label': 'Ticket Number',
        'we_will_reply': 'We will reply to you as soon as possible.',
        'view_ticket_support': 'You can view the ticket in the support section.',
        'reply_sent_success': 'Reply Sent!',
        'your_reply_added': 'Your reply has been added to the ticket.',
        'tariff_selected': 'Tariff Selected',
        'price_label': 'Price',
        'duration_label': 'Duration',
        'payment_methods': 'Select Payment Method',
        'no_payment_methods': 'No payment methods available. Contact support.',
        'back_to_tariffs': 'Back to Tariffs',
        'payment_created_title': 'Payment Created',
        'go_to_payment_text': 'Go to the link to pay:',
        'after_payment': 'After successful payment, the subscription will be activated automatically.',
        'go_to_payment_button': 'Go to Payment',
        'trial_activated_title': 'Trial Activated!',
        'trial_days_received': 'You received 3 days of premium access.',
        'enjoy_vpn': 'Enjoy VPN without restrictions!',
        'registration_success': 'Registration Successful!',
        'your_login_data': 'Your Login Data for Website',
        'important_save': 'IMPORTANT: Save this data! The password will not be shown again.',
        'login_site': 'Login to Website',
        'now_use_bot': 'Now you can use all bot features!',
        'already_registered': 'You are already registered!',
        'registering': 'Registering...',
        'registration_error': 'Registration Error',
        'registration_failed': 'Failed to register. Try again later or register on the website:',
        'ticket_view_title': 'Ticket',
        'status_label': 'Status',
        'subject_label': 'Subject',
        'messages_label': 'Messages',
        'you': 'You',
        'support_label': 'Support',
        'reply_button': 'Reply',
        'back_to_support': 'Back to Support',
        'creating_ticket': 'Creating Ticket',
        'send_subject': 'Send the ticket subject in the next message:',
        'subject_saved': 'Subject saved. Now send the message text:',
        'reply_to_ticket': 'Reply to Ticket',
        'send_reply': 'Send your reply in the next message:',
        'currency_changed': 'Currency Changed',
        'language_changed': 'Language Changed',
        'currency_already_selected': 'This currency is already selected',
        'language_already_selected': 'This language is already selected',
        'invalid_currency': 'Invalid currency',
        'invalid_language': 'Invalid language',
        'failed_to_load': 'Failed to load data',
        'failed_to_load_user': 'Failed to load user data',
        'tariffs_not_found': 'Tariffs not found',
        'tariff_not_found': 'Tariff not found',
        'invalid_tariff_id': 'Error: Invalid tariff ID',
        'link_sent_to_chat': 'Link sent to chat',
        'click_to_copy': 'Click on the link above to copy it.',
        'click_link_to_copy': 'Click on the link above to copy it.',
        'send_ticket_subject': 'Send the ticket subject in the next message',
        'send_your_reply': 'Send your reply in the next message',
        'invalid_ticket_id': 'Error: Invalid ticket ID',
        'ticket_not_found': 'Failed to load ticket',
        'ticket_not_exists': 'The ticket may not exist or you do not have access.',
        'loading_ticket': 'Loading ticket...',
        'unknown': 'Unknown',
        'error_loading': 'Error',
        'on_site': 'on site',
        'or': 'or',
        'activating_trial': 'Activating trial',
        'error_activating_trial': 'Error activating trial',
        'failed_activate_trial': 'Failed to activate trial. Please try again later.',
        'creating_payment': 'Creating payment',
        'error_creating_payment': 'Error creating payment',
    },
    'cn': {
        'main_menu': '主菜单',
        'subscription_status': '订阅状态',
        'tariffs': '套餐',
        'servers': '服务器',
        'referrals': '推荐',
        'support': '支持',
        'settings': '⚙️ 设置',
        'currency': '货币',
        'language': '语言',
        'select_currency': '选择货币:',
        'select_language': '选择语言:',
        'settings_saved': '✅ 设置已保存',
        'back': '🔙 返回',
        'welcome': '欢迎',
        'subscription_active': '活跃',
        'subscription_inactive': '未活跃',
        'expires': '到期',
        'days_left': '剩余天数',
        'traffic': '流量',
        'unlimited': '无限',
        'used': '已使用',
        'login_data': '登录数据',
        'email': '邮箱',
        'password': '密码',
        'connect': '连接',
        'activate_trial': '激活试用',
        'select_tariff': '选择套餐',
        'price': '价格',
        'duration': '时长',
        'days': '天',
        'select_payment': '选择支付方式',
        'payment_created': '支付已创建',
        'go_to_payment': '前往支付',
        'referral_program': '推荐计划',
        'your_referral_link': '您的推荐链接',
        'your_code': '您的代码',
        'copy_link': '复制链接',
        'link_copied': '链接已发送到聊天',
        'support_tickets': '您的工单',
        'create_ticket': '创建工单',
        'ticket_created': '工单已创建',
        'ticket_number': '工单号',
        'subject': '主题',
        'reply': '回复',
        'reply_sent': '回复已发送',
        'servers_list': '服务器列表',
        'online': '在线',
        'offline': '离线',
        'not_registered': '您尚未注册',
        'register': '注册',
        'register_success': '注册成功',
        'trial_activated': '试用已激活',
        'trial_days': '您获得了3天的高级访问权限',
        'error': '错误',
        'auth_error': '授权错误',
        'not_found': '未找到',
        'loading': '加载中...',
        'welcome_bot': '欢迎使用 StealthNET VPN Bot！',
        'not_registered_text': '您尚未在系统中注册。',
        'register_here': '您可以在此处或网站上注册。',
        'after_register': '注册后，您将收到登录名和密码以访问网站。',
        'welcome_user': '欢迎',
        'stealthnet_bot': 'StealthNET VPN Bot',
        'subscription_status_title': '订阅状态',
        'active': '活跃',
        'inactive': '未活跃',
        'expires_at': '到期',
        'days_remaining': '剩余天数',
        'traffic_title': '流量',
        'unlimited_traffic': '无限',
        'traffic_used': '已使用',
        'login_data_title': '网站登录数据',
        'login_label': '登录',
        'password_label': '密码',
        'password_set': '已设置（不可用）',
        'password_not_set': '未设置密码',
        'data_not_found': '未找到数据',
        'connect_button': '连接',
        'activate_trial_button': '激活试用',
        'select_tariff_button': '选择套餐',
        'main_menu_button': '主菜单',
        'status_button': '订阅状态',
        'tariffs_button': '套餐',
        'servers_button': '服务器',
        'referrals_button': '推荐',
        'support_button': '支持',
        'settings_button': '设置',
        'cabinet_button': '办公室',
        'subscription_link': '连接链接',
        'traffic_usage': '流量使用',
        'unlimited_traffic_full': '无限流量',
        'use_login_password': '使用此登录名和密码访问网站',
        'select_tariff_type': '选择套餐类型',
        'basic_tier': '基础',
        'pro_tier': '高级',
        'elite_tier': '精英',
        'from_price': '从',
        'available_options': '可用选项',
        'select_duration': '选择订阅时长',
        'per_day': '天',
        'back_to_type': '返回类型选择',
        'servers_title': '服务器',
        'available_servers': '可用服务器',
        'total_servers': '总服务器数',
        'and_more': '还有',
        'servers_not_found': '未找到服务器',
        'subscription_not_active': '订阅未激活。激活试用或选择套餐',
        'referral_program_title': '推荐计划',
        'invite_friends': '邀请朋友并获得奖励！',
        'your_referral_code': '您的代码',
        'referral_code_not_found': '未找到推荐代码',
        'support_title': '支持',
        'your_tickets': '您的工单',
        'no_tickets': '您还没有工单。',
        'select_action': '选择操作',
        'create_ticket_button': '创建工单',
        'ticket': '工单',
        'ticket_created_success': '工单已创建！',
        'ticket_number_label': '工单号',
        'we_will_reply': '我们会尽快回复您。',
        'view_ticket_support': '您可以在支持部分查看工单。',
        'reply_sent_success': '回复已发送！',
        'your_reply_added': '您的回复已添加到工单。',
        'tariff_selected': '已选择套餐',
        'price_label': '价格',
        'duration_label': '时长',
        'payment_methods': '选择支付方式',
        'no_payment_methods': '没有可用的支付方式。请联系支持。',
        'back_to_tariffs': '返回套餐',
        'payment_created_title': '支付已创建',
        'go_to_payment_text': '转到链接进行支付：',
        'after_payment': '支付成功后，订阅将自动激活。',
        'go_to_payment_button': '前往支付',
        'trial_activated_title': '试用已激活！',
        'trial_days_received': '您获得了3天的高级访问权限。',
        'enjoy_vpn': '享受无限制的VPN！',
        'registration_success': '注册成功！',
        'your_login_data': '您的网站登录数据',
        'important_save': '重要：保存这些数据！密码将不再显示。',
        'login_site': '登录网站',
        'now_use_bot': '现在您可以使用所有机器人功能！',
        'already_registered': '您已经注册！',
        'registering': '注册中...',
        'registration_error': '注册错误',
        'registration_failed': '注册失败。请稍后重试或在网站上注册：',
        'ticket_view_title': '工单',
        'status_label': '状态',
        'subject_label': '主题',
        'messages_label': '消息',
        'you': '您',
        'support_label': '支持',
        'reply_button': '回复',
        'back_to_support': '返回支持',
        'creating_ticket': '创建工单',
        'send_subject': '在下一个消息中发送工单主题：',
        'subject_saved': '主题已保存。现在发送消息文本：',
        'reply_to_ticket': '回复工单',
        'send_reply': '在下一个消息中发送您的回复：',
        'currency_changed': '货币已更改',
        'language_changed': '语言已更改',
        'currency_already_selected': '此货币已选择',
        'language_already_selected': '此语言已选择',
        'invalid_currency': '无效货币',
        'invalid_language': '无效语言',
        'failed_to_load': '加载数据失败',
        'failed_to_load_user': '加载用户数据失败',
        'tariffs_not_found': '未找到套餐',
        'tariff_not_found': '未找到套餐',
        'invalid_tariff_id': '错误：无效的套餐ID',
        'link_sent_to_chat': '链接已发送到聊天',
        'click_to_copy': '点击上面的链接以复制它。',
        'click_link_to_copy': '点击上面的链接以复制它。',
        'send_ticket_subject': '在下一个消息中发送工单主题',
        'send_your_reply': '在下一个消息中发送您的回复',
        'invalid_ticket_id': '错误：无效的工单ID',
        'ticket_not_found': '加载工单失败',
        'ticket_not_exists': '工单可能不存在或您没有访问权限。',
        'loading_ticket': '加载工单中...',
        'unknown': '未知',
        'error_loading': '错误',
        'on_site': '在网站上',
        'or': '或',
        'activating_trial': '正在激活试用',
        'error_activating_trial': '激活试用时出错',
        'failed_activate_trial': '无法激活试用。请稍后再试。',
        'creating_payment': '正在创建支付',
        'error_creating_payment': '创建支付时出错',
    }
}

def get_text(key: str, lang: str = 'ru') -> str:
    """Получить переведенный текст"""
    return TRANSLATIONS.get(lang, TRANSLATIONS['ru']).get(key, key)

def get_user_lang(user_data: dict = None, context: ContextTypes.DEFAULT_TYPE = None, token: str = None) -> str:
    """Получить язык пользователя из данных, context или по токену"""
    # Сначала проверяем context.user_data (самый быстрый способ, если язык был недавно изменен)
    if context and hasattr(context, 'user_data') and 'user_lang' in context.user_data:
        lang = context.user_data['user_lang']
        if lang in ['ru', 'ua', 'en', 'cn']:
            return lang
    
    # Затем проверяем user_data
    if user_data:
        lang = user_data.get('preferred_lang') or user_data.get('preferredLang') or 'ru'
        if lang in ['ru', 'ua', 'en', 'cn']:
            # Сохраняем в context для следующего раза
            if context and hasattr(context, 'user_data'):
                context.user_data['user_lang'] = lang
            return lang
    
    # Если есть token, получаем данные из API
    if token:
        user_data = api.get_user_data(token)
        if user_data:
            lang = user_data.get('preferred_lang') or user_data.get('preferredLang') or 'ru'
            if lang in ['ru', 'ua', 'en', 'cn']:
                # Сохраняем в context для следующего раза
                if context and hasattr(context, 'user_data'):
                    context.user_data['user_lang'] = lang
                return lang
    
    # По умолчанию русский
    return 'ru'


def get_user_token(telegram_id: int) -> Optional[str]:
    """Получить или создать JWT токен для пользователя"""
    if telegram_id in user_tokens:
        return user_tokens[telegram_id]
    
    # Получаем токен через API
    token = api.get_user_by_telegram_id(telegram_id)
    if token:
        user_tokens[telegram_id] = token
        return token
    
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    telegram_id = user.id
    
    # Получаем токен для пользователя
    token = get_user_token(telegram_id)
    
    if not token:
        # Пользователь не зарегистрирован - предлагаем регистрацию
        # Используем русский язык по умолчанию для незарегистрированных пользователей
        lang = 'ru'
        keyboard = [
            [
                InlineKeyboardButton(f"✅ {get_text('register', lang)}", callback_data="register_user")
            ],
            [
                InlineKeyboardButton(f"🌐 {get_text('register', lang)} {get_text('on_site', lang)}", url="https://panel.stealthnet.app/register")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"👋 {get_text('welcome_bot', lang)}\n\n"
        text += f"❌ {get_text('not_registered_text', lang)}\n\n"
        text += f"📝 {get_text('register_here', lang)}\n\n"
        text += f"💡 {get_text('after_register', lang)}"
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return
    
    # Получаем данные пользователя
    user_data = api.get_user_data(token)
    
    if not user_data:
        lang = get_user_lang(None, context, token)
        await update.message.reply_text(f"❌ {get_text('failed_to_load_user', lang)}")
        return
    
    # Получаем язык пользователя
    user_lang = get_user_lang(user_data, context, token)
    
    # Получаем данные для входа
    credentials = api.get_credentials(telegram_id)
    
    # Формируем приветственное сообщение с подробной информацией
    welcome_text = f"🛡️ **{get_text('stealthnet_bot', user_lang)}**\n"
    welcome_text += f"👋 {get_text('welcome_user', user_lang)}, {user.first_name}!\n\n"
    welcome_text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Статус подписки
    is_active = user_data.get("activeInternalSquads", [])
    expire_at = user_data.get("expireAt")
    subscription_url = user_data.get("subscriptionUrl", "")
    used_traffic = user_data.get("usedTrafficBytes", 0)
    traffic_limit = user_data.get("trafficLimitBytes", 0)
    
    if is_active and expire_at:
        expire_date = datetime.fromisoformat(expire_at.replace('Z', '+00:00'))
        days_left = (expire_date - datetime.now(expire_date.tzinfo)).days
        
        # Статус с индикатором - современный дизайн
        status_icon = "🟢" if days_left > 7 else "🟡" if days_left > 0 else "🔴"
        welcome_text += f"📊 **{get_text('subscription_status_title', user_lang)}**\n"
        welcome_text += f"{status_icon} {get_text('active', user_lang)}\n"
        welcome_text += f"📅 {expire_date.strftime('%d.%m.%Y %H:%M')}\n"
        welcome_text += f"⏰ {days_left} {get_text('days', user_lang)}\n\n"
        
        # Трафик с прогресс-баром - современный дизайн
        welcome_text += f"📈 **{get_text('traffic_title', user_lang)}**\n"
        if traffic_limit == 0:
            welcome_text += f"♾️ {get_text('unlimited_traffic', user_lang)}\n\n"
        else:
            used_gb = used_traffic / (1024 ** 3)
            limit_gb = traffic_limit / (1024 ** 3)
            percentage = (used_traffic / traffic_limit * 100) if traffic_limit > 0 else 0
            
            # Прогресс-бар (15 блоков)
            filled = int(percentage / (100 / 15))
            filled = min(filled, 15)
            progress_bar = "█" * filled + "░" * (15 - filled)
            progress_color = "🟢" if percentage < 70 else "🟡" if percentage < 90 else "🔴"
            
            welcome_text += f"{progress_color} {progress_bar} {percentage:.0f}%\n"
            welcome_text += f"📥 {used_gb:.2f} / {limit_gb:.2f} GB\n\n"
    else:
        welcome_text += f"📊 **{get_text('subscription_status_title', user_lang)}**\n"
        welcome_text += f"🔴 {get_text('inactive', user_lang)}\n"
        welcome_text += f"💡 {get_text('activate_trial_button', user_lang)}\n\n"
    
    # Данные для входа на сайте - современный дизайн
    welcome_text += f"🔐 **{get_text('login_data_title', user_lang)}**\n"
    if credentials and credentials.get("email"):
        welcome_text += f"📧 `{credentials['email']}`\n"
        if credentials.get("password"):
            welcome_text += f"🔑 `{credentials['password']}`\n"
        elif credentials.get("has_password"):
            welcome_text += f"🔑 {get_text('password_set', user_lang)}\n"
        else:
            welcome_text += f"⚠️ {get_text('password_not_set', user_lang)}\n"
    else:
        welcome_text += f"❌ {get_text('data_not_found', user_lang)}\n"
    
    # Кнопки главного меню
    keyboard = []
    
    # Кнопка подключения (если есть активная подписка и ссылка)
    if is_active and subscription_url:
        keyboard.append([
            InlineKeyboardButton(f"🚀 {get_text('connect_button', user_lang)}", url=subscription_url)
        ])
    
    # Кнопка активации триала (если подписка не активна)
    if not is_active or not expire_at:
        keyboard.append([
            InlineKeyboardButton(f"🎁 {get_text('activate_trial_button', user_lang)}", callback_data="activate_trial")
        ])
    
    keyboard.extend([
        [
            InlineKeyboardButton(f"📊 {get_text('status_button', user_lang)}", callback_data="status"),
            InlineKeyboardButton(f"💎 {get_text('tariffs_button', user_lang)}", callback_data="tariffs")
        ],
        [
            InlineKeyboardButton(f"🌐 {get_text('servers_button', user_lang)}", callback_data="servers"),
            InlineKeyboardButton(f"🎁 {get_text('referrals_button', user_lang)}", callback_data="referrals")
        ],
        [
            InlineKeyboardButton(f"💬 {get_text('support_button', user_lang)}", callback_data="support"),
            InlineKeyboardButton(f"⚙️ {get_text('settings_button', user_lang)}", callback_data="settings")
        ]
    ])
    
    # Добавляем Web App кнопку, если URL настроен
    if MINIAPP_URL and MINIAPP_URL.startswith("https://"):
        keyboard.append([
            InlineKeyboardButton(f"📱 {get_text('cabinet_button', user_lang)}", web_app=WebAppInfo(url=MINIAPP_URL))
        ])
    else:
        logger.warning(f"MINIAPP_URL не настроен или не HTTPS: {MINIAPP_URL}")
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(welcome_text):
        welcome_text_clean = clean_markdown_for_cards(welcome_text)
        await update.message.reply_text(
            welcome_text_clean,
            reply_markup=reply_markup
        )
    else:
        # Для текста без карточек используем Markdown
        try:
            await update.message.reply_text(
                welcome_text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Markdown parsing error, sending without formatting: {e}")
            await update.message.reply_text(
                clean_markdown_for_cards(welcome_text),
                reply_markup=reply_markup
            )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status"""
    await show_status(update, context)


async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статус подписки"""
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        lang = get_user_lang(None, context, token)
        await update.callback_query.answer(f"❌ {get_text('auth_error', lang)}")
        return
    
    user_data = api.get_user_data(token)
    if not user_data:
        lang = get_user_lang(None, context, token)
        await update.callback_query.answer(f"❌ {get_text('failed_to_load', lang)}")
        return
    
    # Получаем язык пользователя
    user_lang = get_user_lang(user_data, context, token)
    
    # Формируем сообщение со статусом
    is_active = user_data.get("activeInternalSquads", [])
    expire_at = user_data.get("expireAt")
    used_traffic = user_data.get("usedTrafficBytes", 0)
    traffic_limit = user_data.get("trafficLimitBytes", 0)
    subscription_url = user_data.get("subscriptionUrl", "")
    
    status_text = f"📊 **{get_text('subscription_status_title', user_lang)}**\n"
    status_text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if is_active and expire_at:
        expire_date = datetime.fromisoformat(expire_at.replace('Z', '+00:00'))
        days_left = (expire_date - datetime.now(expire_date.tzinfo)).days
        
        # Статус - современный дизайн
        status_icon = "🟢" if days_left > 7 else "🟡" if days_left > 0 else "🔴"
        status_text += f"{status_icon} **{get_text('active', user_lang)}**\n"
        status_text += f"📅 {expire_date.strftime('%d.%m.%Y %H:%M')}\n"
        status_text += f"⏰ {days_left} {get_text('days', user_lang)}\n\n"
        
        if subscription_url:
            status_text += f"🔗 **{get_text('subscription_link', user_lang)}**\n"
            status_text += f"`{subscription_url}`\n\n"
    else:
        status_text += f"🔴 **{get_text('inactive', user_lang)}**\n"
        status_text += f"💡 {get_text('subscription_not_active', user_lang)}\n\n"
    
    # Трафик с прогресс-баром - современный дизайн
    status_text += f"📈 **{get_text('traffic_usage', user_lang)}**\n"
    if traffic_limit == 0:
        status_text += f"♾️ {get_text('unlimited_traffic_full', user_lang)}\n\n"
    else:
        used_gb = used_traffic / (1024 ** 3)
        limit_gb = traffic_limit / (1024 ** 3)
        percentage = (used_traffic / traffic_limit * 100) if traffic_limit > 0 else 0
        
        # Прогресс-бар (15 блоков)
        filled = int(percentage / (100 / 15))
        filled = min(filled, 15)
        progress_bar = "█" * filled + "░" * (15 - filled)
        progress_color = "🟢" if percentage < 70 else "🟡" if percentage < 90 else "🔴"
        
        status_text += f"{progress_color} {progress_bar} {percentage:.0f}%\n"
        status_text += f"📥 {used_gb:.2f} / {limit_gb:.2f} GB\n\n"
    
    # Данные для входа - современный дизайн
    status_text += "━━━━━━━━━━━━━━━━━━━━\n"
    status_text += f"🔐 **{get_text('login_data_title', user_lang)}**\n"
    
    credentials = api.get_credentials(telegram_id)
    if credentials and credentials.get("email"):
        status_text += f"📧 `{credentials['email']}`\n"
        if credentials.get("password"):
            status_text += f"🔑 `{credentials['password']}`\n\n"
            status_text += f"💡 {get_text('use_login_password', user_lang)}\n"
            status_text += "🌐 https://panel.stealthnet.app\n"
        elif credentials.get("has_password"):
            status_text += f"🔑 {get_text('password_set', user_lang)}\n\n"
            status_text += f"💡 {get_text('use_login_password', user_lang)}\n"
            status_text += "🌐 https://panel.stealthnet.app\n"
        else:
            status_text += f"⚠️ {get_text('password_not_set', user_lang)}\n"
    else:
        status_text += f"❌ {get_text('data_not_found', user_lang)}\n"
    
    # Кнопки действий
    keyboard = []
    
    # Кнопка подключения (если есть активная подписка и ссылка)
    if is_active and subscription_url:
        keyboard.append([
            InlineKeyboardButton(f"🚀 {get_text('connect_button', user_lang)}", url=subscription_url)
        ])
    
    keyboard.append([
        InlineKeyboardButton(f"💎 {get_text('select_tariff_button', user_lang)}", callback_data="tariffs"),
        InlineKeyboardButton(f"🔙 {get_text('main_menu_button', user_lang)}", callback_data="main_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(status_text):
        status_text_clean = clean_markdown_for_cards(status_text)
        if update.callback_query:
            await update.callback_query.edit_message_text(
                status_text_clean,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                status_text_clean,
                reply_markup=reply_markup
            )
    else:
        # Для текста без карточек используем Markdown
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    status_text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    status_text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.warning(f"Markdown parsing error in show_status, sending without formatting: {e}")
            status_text_clean = clean_markdown_for_cards(status_text)
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    status_text_clean,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    status_text_clean,
                    reply_markup=reply_markup
                )


async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать выбор типа тарифа (Basic/Pro/Elite)"""
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        await update.callback_query.answer("❌ Ошибка авторизации")
        return
    
    tariffs = api.get_tariffs()
    
    if not tariffs:
        await update.callback_query.answer("❌ Тарифы не найдены")
        return
    
    # Получаем валюту пользователя
    user_data = api.get_user_data(token)
    currency = user_data.get("preferred_currency", "uah") if user_data else "uah"
    
    currency_map = {
        "uah": {"field": "price_uah", "symbol": "₴"},
        "rub": {"field": "price_rub", "symbol": "₽"},
        "usd": {"field": "price_usd", "symbol": "$"}
    }
    
    currency_config = currency_map.get(currency, currency_map["uah"])
    symbol = currency_config["symbol"]
    
    # Группируем тарифы по tier и находим минимальные цены
    basic_tariffs = []
    pro_tariffs = []
    elite_tariffs = []
    
    for tariff in tariffs:
        duration = tariff.get("duration_days", 0)
        tier = tariff.get("tier")
        
        if not tier:
            # Определяем tier по длительности
            if duration >= 180:
                tier = "elite"
            elif duration >= 90:
                tier = "pro"
            else:
                tier = "basic"
        
        tariff["_tier"] = tier
        
        if tier == "elite":
            elite_tariffs.append(tariff)
        elif tier == "pro":
            pro_tariffs.append(tariff)
        else:
            basic_tariffs.append(tariff)
    
    # Формируем сообщение с выбором типа тарифа
    text = "💎 **Тарифные планы**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Показываем краткую информацию о каждом типе в современном стиле
    if basic_tariffs:
        min_price = min(t.get(currency_config["field"], 0) for t in basic_tariffs)
        text += f"📦 **Базовый**\n"
        text += f"💰 От {min_price:.0f} {symbol}\n"
        text += f"📦 {len(basic_tariffs)} вариантов\n\n"
    
    if pro_tariffs:
        min_price = min(t.get(currency_config["field"], 0) for t in pro_tariffs)
        text += f"⭐ **Премиум**\n"
        text += f"💰 От {min_price:.0f} {symbol}\n"
        text += f"📦 {len(pro_tariffs)} вариантов\n\n"
    
    if elite_tariffs:
        min_price = min(t.get(currency_config["field"], 0) for t in elite_tariffs)
        text += f"👑 **Элитный**\n"
        text += f"💰 От {min_price:.0f} {symbol}\n"
        text += f"📦 {len(elite_tariffs)} вариантов\n\n"
    
    # Кнопки выбора типа тарифа
    keyboard = []
    if basic_tariffs:
        keyboard.append([InlineKeyboardButton("📦 Базовый", callback_data="tier_basic")])
    if pro_tariffs:
        keyboard.append([InlineKeyboardButton("⭐ Премиум", callback_data="tier_pro")])
    if elite_tariffs:
        keyboard.append([InlineKeyboardButton("👑 Элитный", callback_data="tier_elite")])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(text):
        text_clean = clean_markdown_for_cards(text)
        await update.callback_query.edit_message_text(
            text_clean,
            reply_markup=reply_markup
        )
    else:
        # Для текста без карточек используем Markdown
        try:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Markdown parsing error in show_tariffs, sending without formatting: {e}")
            await update.callback_query.edit_message_text(
                clean_markdown_for_cards(text),
                reply_markup=reply_markup
            )


async def show_tier_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE, tier: str):
    """Показать тарифы конкретного типа (Basic/Pro/Elite) с выбором длительности"""
    query = update.callback_query
    if not query:
        return
    
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        await query.answer("❌ Ошибка авторизации")
        return
    
    tariffs = api.get_tariffs()
    
    if not tariffs:
        await query.answer("❌ Тарифы не найдены")
        return
    
    # Получаем валюту пользователя
    user_data = api.get_user_data(token)
    currency = user_data.get("preferred_currency", "uah") if user_data else "uah"
    
    currency_map = {
        "uah": {"field": "price_uah", "symbol": "₴"},
        "rub": {"field": "price_rub", "symbol": "₽"},
        "usd": {"field": "price_usd", "symbol": "$"}
    }
    
    currency_config = currency_map.get(currency, currency_map["uah"])
    price_field = currency_config["field"]
    symbol = currency_config["symbol"]
    
    # Фильтруем тарифы по tier
    tier_tariffs = []
    tier_names = {
        "basic": "📦 Базовый",
        "pro": "⭐ Премиум",
        "elite": "👑 Элитный"
    }
    
    for tariff in tariffs:
        duration = tariff.get("duration_days", 0)
        tariff_tier = tariff.get("tier")
        
        if not tariff_tier:
            # Определяем tier по длительности
            if duration >= 180:
                tariff_tier = "elite"
            elif duration >= 90:
                tariff_tier = "pro"
            else:
                tariff_tier = "basic"
        
        if tariff_tier == tier:
            tier_tariffs.append(tariff)
    
    if not tier_tariffs:
        await query.answer("❌ Тарифы этого типа не найдены")
        return
    
    # Сортируем по длительности
    tier_tariffs.sort(key=lambda x: x.get("duration_days", 0))
    
    # Формируем сообщение
    tier_name = tier_names.get(tier, tier.capitalize())
    text = f"{tier_name} **тарифы**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "📅 Выберите длительность:\n\n"
    
    # Показываем список тарифов в современном стиле
    for tariff in tier_tariffs:
        name = tariff.get("name", f"{tariff.get('duration_days', 0)} дней")
        price = tariff.get(price_field, 0)
        duration = tariff.get("duration_days", 0)
        per_day = price / duration if duration > 0 else price
        
        text += f"📦 **{name}**\n"
        text += f"💰 {price:.0f} {symbol}\n"
        text += f"📊 {per_day:.2f} {symbol}/день\n"
        text += f"⏱️ {duration} дней\n\n"
    
    # Кнопки выбора длительности
    keyboard = []
    row = []
    for tariff in tier_tariffs:
        duration = tariff.get("duration_days", 0)
        name = f"{duration} дн."
        if len(name) > 15:
            name = f"{duration}д"
        
        row.append(InlineKeyboardButton(
            name,
            callback_data=f"tariff_{tariff.get('id')}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("🔙 К выбору типа", callback_data="tariffs")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(text):
        text_clean = clean_markdown_for_cards(text)
        await query.edit_message_text(
            text_clean,
            reply_markup=reply_markup
        )
    else:
        # Для текста без карточек используем Markdown
        try:
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Markdown parsing error, sending without formatting: {e}")
            await query.edit_message_text(
                clean_markdown_for_cards(text),
                reply_markup=reply_markup
            )


async def show_servers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список серверов"""
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        await update.callback_query.answer("❌ Ошибка авторизации")
        return
    
    # Проверяем активность подписки
    user_data = api.get_user_data(token)
    if not user_data:
        await update.callback_query.answer("❌ Не удалось загрузить данные")
        return
    
    is_active = user_data.get("activeInternalSquads", [])
    expire_at = user_data.get("expireAt")
    
    if not is_active or not expire_at:
        await update.callback_query.answer("❌ Подписка не активна. Активируйте триал или выберите тариф")
        return
    
    nodes = api.get_nodes(token)
    
    if not nodes:
        text = "🌐 **Серверы**\n\n❌ Серверы не найдены"
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # Если текст содержит карточки, убираем Markdown-форматирование
        if has_cards(text):
            text_clean = clean_markdown_for_cards(text)
            await update.callback_query.edit_message_text(text_clean, reply_markup=reply_markup)
        else:
            try:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"Markdown parsing error, sending without formatting: {e}")
                await update.callback_query.edit_message_text(clean_markdown_for_cards(text), reply_markup=reply_markup)
        return
    
    # Формируем сообщение
    text = f"🌐 **Доступные серверы**\n\n"
    text += f"Всего серверов: {len(nodes)}\n\n"
    
    # Группируем по регионам
    regions = {}
    for node in nodes[:20]:  # Показываем первые 20
        region = node.get("regionName") or node.get("countryCode", "Unknown")
        if region not in regions:
            regions[region] = []
        regions[region].append(node)
    
    for region, region_nodes in list(regions.items())[:5]:  # Показываем первые 5 регионов
        text += f"📍 **{region}** ({len(region_nodes)} серверов)\n"
        for node in region_nodes[:3]:  # По 3 сервера на регион
            name = node.get("nodeName", "Unknown")
            text += f"  • {name}\n"
        text += "\n"
    
    if len(nodes) > 20:
        text += f"\n... и еще {len(nodes) - 20} серверов"
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(text):
        text_clean = clean_markdown_for_cards(text)
        await update.callback_query.edit_message_text(
            text_clean,
            reply_markup=reply_markup
        )
    else:
        # Для текста без карточек используем Markdown
        try:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Markdown parsing error in show_tariffs, sending without formatting: {e}")
            await update.callback_query.edit_message_text(
                clean_markdown_for_cards(text),
                reply_markup=reply_markup
            )


async def show_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать реферальную программу"""
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        await update.callback_query.answer("❌ Ошибка авторизации")
        return
    
    user_data = api.get_user_data(token)
    if not user_data:
        await update.callback_query.answer("❌ Не удалось загрузить данные")
        return
    
    # Получаем язык пользователя
    user_lang = get_user_lang(user_data, context, token)
    
    referral_code = user_data.get("referral_code", "")
    
    # Получаем домен сервера из API
    try:
        domain_resp = api.session.get(f"{FLASK_API_URL}/api/public/server-domain", timeout=5)
        if domain_resp.status_code == 200:
            domain_data = domain_resp.json()
            server_domain = domain_data.get("full_url") or domain_data.get("domain") or "panel.stealthnet.app"
        else:
            server_domain = "panel.stealthnet.app"
    except:
        server_domain = "panel.stealthnet.app"
    
    # Формируем ссылку
    if referral_code:
        if not server_domain.startswith("http"):
            server_domain = f"https://{server_domain}"
        referral_link = f"{server_domain}/register?ref={referral_code}"
    else:
        referral_link = ""
    
    text = f"🎁 **{get_text('referral_program', user_lang)}**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"💡 {get_text('invite_friends_bonus', user_lang)}\n\n"
    
    if referral_code:
        # Современный дизайн для реферальной ссылки
        text += f"🔗 **{get_text('your_referral_link', user_lang)}**\n"
        text += f"`{referral_link}`\n\n"
        
        # Код
        text += f"📝 **{get_text('your_code', user_lang)}**\n"
        text += f"`{referral_code}`\n"
    else:
        text += f"❌ {get_text('referral_code_not_found', user_lang)}\n"
    
    keyboard = [
        [InlineKeyboardButton(f"📋 {get_text('copy_link', user_lang)}", callback_data=f"copy_ref_{referral_code}")],
        [InlineKeyboardButton(f"🔙 {get_text('main_menu_button', user_lang)}", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(text):
        text_clean = clean_markdown_for_cards(text)
        await update.callback_query.edit_message_text(
            text_clean,
            reply_markup=reply_markup
        )
    else:
        # Для текста без карточек используем Markdown
        try:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Markdown parsing error in show_tariffs, sending without formatting: {e}")
            await update.callback_query.edit_message_text(
                clean_markdown_for_cards(text),
                reply_markup=reply_markup
            )


async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать поддержку"""
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        lang = get_user_lang(None, context, token)
        await update.callback_query.answer(f"❌ {get_text('auth_error', lang)}")
        return
    
    tickets = api.get_support_tickets(token)
    
    user_data = api.get_user_data(token)
    user_lang = get_user_lang(user_data, context, token)
    
    text = f"💬 **{get_text('support_title', user_lang)}**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if tickets:
        text += f"📋 **{get_text('your_tickets', user_lang)}:** ({len(tickets)})\n\n"
        for ticket in tickets[:5]:
            status_emoji = "✅" if ticket.get("status") == "CLOSED" else "🔄"
            ticket_id = ticket.get('id')
            subject = ticket.get('subject', get_text('no_subject', user_lang))
            text += f"{status_emoji} {get_text('ticket', user_lang)} #{ticket_id}: {subject}\n"
    else:
        text += f"{get_text('no_tickets', user_lang)}\n"
    
    text += f"\n**{get_text('select_action', user_lang)}**:"
    
    keyboard = [
        [InlineKeyboardButton(f"➕ {get_text('create_ticket_button', user_lang)}", callback_data="create_ticket")]
    ]
    
    # Добавляем кнопки для просмотра тикетов, если они есть
    if tickets:
        for ticket in tickets[:3]:  # Показываем первые 3 тикета
            ticket_id = ticket.get('id')
            subject = ticket.get('subject', get_text('no_subject', user_lang))
            # Обрезаем длинные темы
            if len(subject) > 30:
                subject = subject[:27] + "..."
            keyboard.append([
                InlineKeyboardButton(
                    f"📋 #{ticket_id}: {subject}",
                    callback_data=f"view_ticket_{ticket_id}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton(f"🔙 {get_text('main_menu_button', user_lang)}", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(text):
        text_clean = clean_markdown_for_cards(text)
        await update.callback_query.edit_message_text(
            text_clean,
            reply_markup=reply_markup
        )
    else:
        # Для текста без карточек используем Markdown
        try:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Markdown parsing error in show_tariffs, sending without formatting: {e}")
            await update.callback_query.edit_message_text(
                clean_markdown_for_cards(text),
                reply_markup=reply_markup
            )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline кнопки"""
    query = update.callback_query
    if not query:
        return
    
    data = query.data
    
    # Игнорируем платежные callback'и - они обрабатываются отдельным обработчиком
    if data and data.startswith("pay_"):
        return
    
    # Пытаемся ответить на callback query, но игнорируем ошибки если query слишком старый
    try:
        await query.answer()
    except Exception as e:
        # Игнорируем ошибки "Query is too old" - это нормально, если бот был перезапущен
        if "too old" not in str(e).lower() and "timeout" not in str(e).lower():
            logger.warning(f"Error answering callback query: {e}")
        # Продолжаем выполнение даже если не удалось ответить
    
    if data == "main_menu":
        # Возвращаемся к главному меню с полной информацией
        user = update.effective_user
        telegram_id = user.id
        
        token = get_user_token(telegram_id)
        if token:
            user_data = api.get_user_data(token)
            credentials = api.get_credentials(telegram_id)
            
            if user_data:
                # Получаем язык пользователя
                user_lang = get_user_lang(user_data, context, token)
                
                welcome_text = f"🛡️ **{get_text('stealthnet_bot', user_lang)}**\n"
                welcome_text += f"👋 {get_text('main_menu_button', user_lang)}\n\n"
                welcome_text += "━━━━━━━━━━━━━━━━━━━━\n\n"
                
                # Статус подписки
                is_active = user_data.get("activeInternalSquads", [])
                expire_at = user_data.get("expireAt")
                subscription_url = user_data.get("subscriptionUrl", "")
                used_traffic = user_data.get("usedTrafficBytes", 0)
                traffic_limit = user_data.get("trafficLimitBytes", 0)
                
                if is_active and expire_at:
                    expire_date = datetime.fromisoformat(expire_at.replace('Z', '+00:00'))
                    days_left = (expire_date - datetime.now(expire_date.tzinfo)).days
                    
                    status_icon = "🟢" if days_left > 7 else "🟡" if days_left > 0 else "🔴"
                    welcome_text += f"📊 **{get_text('subscription_status_title', user_lang)}**\n"
                    welcome_text += f"{status_icon} {get_text('active', user_lang)}\n"
                    welcome_text += f"📅 {expire_date.strftime('%d.%m.%Y %H:%M')}\n"
                    welcome_text += f"⏰ {days_left} {get_text('days', user_lang)}\n\n"
                    
                    # Трафик
                    welcome_text += f"📈 **{get_text('traffic_title', user_lang)}**\n"
                    if traffic_limit == 0:
                        welcome_text += f"♾️ {get_text('unlimited_traffic', user_lang)}\n\n"
                    else:
                        used_gb = used_traffic / (1024 ** 3)
                        limit_gb = traffic_limit / (1024 ** 3)
                        percentage = (used_traffic / traffic_limit * 100) if traffic_limit > 0 else 0
                        
                        filled = int(percentage / (100 / 15))
                        filled = min(filled, 15)
                        progress_bar = "█" * filled + "░" * (15 - filled)
                        progress_color = "🟢" if percentage < 70 else "🟡" if percentage < 90 else "🔴"
                        
                        welcome_text += f"{progress_color} {progress_bar} {percentage:.0f}%\n"
                        welcome_text += f"📥 {used_gb:.2f} / {limit_gb:.2f} GB\n\n"
                else:
                    welcome_text += f"📊 **{get_text('subscription_status_title', user_lang)}**\n"
                    welcome_text += f"🔴 {get_text('inactive', user_lang)}\n\n"
                
                # Данные для входа
                welcome_text += f"🔐 **{get_text('login_data_title', user_lang)}**\n"
                if credentials and credentials.get("email"):
                    welcome_text += f"📧 `{credentials['email']}`\n"
                    if credentials.get("password"):
                        welcome_text += f"🔑 `{credentials['password']}`\n"
                    elif credentials.get("has_password"):
                        welcome_text += f"🔑 {get_text('password_set', user_lang)}\n"
                welcome_text += "\n"
                
                keyboard = []
                
                # Кнопка подключения
                if is_active and subscription_url:
                    keyboard.append([
                        InlineKeyboardButton(f"🚀 {get_text('connect_button', user_lang)}", url=subscription_url)
                    ])
                
                # Кнопка активации триала (если подписка не активна)
                if not is_active or not expire_at:
                    keyboard.append([
                        InlineKeyboardButton(f"🎁 {get_text('activate_trial_button', user_lang)}", callback_data="activate_trial")
                    ])
                
                keyboard.extend([
                    [
                        InlineKeyboardButton(f"📊 {get_text('status_button', user_lang)}", callback_data="status"),
                        InlineKeyboardButton(f"💎 {get_text('tariffs_button', user_lang)}", callback_data="tariffs")
                    ],
                    [
                        InlineKeyboardButton(f"🌐 {get_text('servers_button', user_lang)}", callback_data="servers"),
                        InlineKeyboardButton(f"🎁 {get_text('referrals_button', user_lang)}", callback_data="referrals")
                    ],
                    [
                        InlineKeyboardButton(f"💬 {get_text('support_button', user_lang)}", callback_data="support"),
                        InlineKeyboardButton(f"⚙️ {get_text('settings_button', user_lang)}", callback_data="settings")
                    ]
                ])
                
                # Web App кнопка
                if MINIAPP_URL and MINIAPP_URL.startswith("https://"):
                    keyboard.append([
                        InlineKeyboardButton(f"📱 {get_text('cabinet_button', user_lang)}", web_app=WebAppInfo(url=MINIAPP_URL))
                    ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Если текст содержит карточки, убираем Markdown-форматирование
                if has_cards(welcome_text):
                    welcome_text_clean = clean_markdown_for_cards(welcome_text)
                    await query.edit_message_text(welcome_text_clean, reply_markup=reply_markup)
                else:
                    try:
                        await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
                    except Exception as e:
                        logger.warning(f"Markdown parsing error in main_menu, sending without formatting: {e}")
                        await query.edit_message_text(
                            clean_markdown_for_cards(welcome_text),
                            reply_markup=reply_markup
                        )
                return
        
        # Fallback если не удалось загрузить данные
        lang = get_user_lang(None, context, token) if token else 'ru'
        welcome_text = f"👋 {get_text('main_menu_button', lang)}\n\n"
        welcome_text += f"{get_text('select_action', lang)}:"
        
        keyboard = [
            [
                InlineKeyboardButton(f"📊 {get_text('status_button', lang)}", callback_data="status"),
                InlineKeyboardButton(f"💎 {get_text('tariffs_button', lang)}", callback_data="tariffs")
            ],
            [
                InlineKeyboardButton(f"🌐 {get_text('servers_button', lang)}", callback_data="servers"),
                InlineKeyboardButton(f"🎁 {get_text('referrals_button', lang)}", callback_data="referrals")
            ],
            [
                InlineKeyboardButton(f"💬 {get_text('support_button', lang)}", callback_data="support"),
                InlineKeyboardButton(f"⚙️ {get_text('settings_button', lang)}", callback_data="settings")
            ]
        ]
        
        if MINIAPP_URL and MINIAPP_URL.startswith("https://"):
            keyboard.append([
                InlineKeyboardButton(f"📱 {get_text('cabinet_button', lang)}", web_app=WebAppInfo(url=MINIAPP_URL))
            ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(welcome_text, reply_markup=reply_markup)
    
    elif data == "status":
        await show_status(update, context)
    
    elif data == "tariffs":
        await show_tariffs(update, context)
    
    elif data.startswith("tier_"):
        tier = data.replace("tier_", "")
        await show_tier_tariffs(update, context, tier)
    
    elif data == "servers":
        await show_servers(update, context)
    
    elif data == "referrals":
        await show_referrals(update, context)
    
    elif data == "support":
        await show_support(update, context)
    
    elif data == "activate_trial":
        await activate_trial(update, context)
    
    elif data.startswith("tariff_"):
        try:
            tariff_id = int(data.split("_")[1])
            await select_tariff(update, context, tariff_id)
        except (ValueError, IndexError):
            await query.answer("❌ Ошибка: неверный ID тарифа")
    
    elif data.startswith("copy_ref_"):
        referral_code = data.replace("copy_ref_", "")
        
        user = update.effective_user
        telegram_id = user.id
        token = get_user_token(telegram_id)
        user_data = api.get_user_data(token) if token else None
        user_lang = get_user_lang(user_data, context, token)
        
        # Получаем домен сервера из API
        try:
            domain_resp = api.session.get(f"{FLASK_API_URL}/api/public/server-domain", timeout=5)
            if domain_resp.status_code == 200:
                domain_data = domain_resp.json()
                server_domain = domain_data.get("full_url") or domain_data.get("domain") or "panel.stealthnet.app"
            else:
                server_domain = "panel.stealthnet.app"
        except:
            server_domain = "panel.stealthnet.app"
        
        # Формируем ссылку
        if not server_domain.startswith("http"):
            server_domain = f"https://{server_domain}"
        referral_link = f"{server_domain}/register?ref={referral_code}"
        
        # Отправляем ссылку отдельным сообщением для удобного копирования
        await query.answer(f"✅ {get_text('link_sent_to_chat', user_lang)}", show_alert=False)
        await query.message.reply_text(
            f"🔗 **{get_text('your_referral_link', user_lang)}**\n\n"
            f"`{referral_link}`\n\n"
            f"{get_text('click_link_to_copy', user_lang)}.",
            parse_mode="Markdown"
        )
    
    elif data == "create_ticket":
        user = update.effective_user
        telegram_id = user.id
        token = get_user_token(telegram_id)
        user_data = api.get_user_data(token) if token else None
        user_lang = get_user_lang(user_data, context, token)
        
        await query.edit_message_text(
            f"💬 **{get_text('creating_ticket', user_lang)}**\n\n"
            f"{get_text('send_ticket_subject', user_lang)}:",
            parse_mode="Markdown"
        )
        context.user_data["waiting_for_ticket_subject"] = True
    
    elif data.startswith("view_ticket_"):
        try:
            ticket_id = int(data.replace("view_ticket_", ""))
            await view_ticket(update, context, ticket_id)
        except (ValueError, IndexError):
            await query.answer("❌ Ошибка: неверный ID тикета")
    
    elif data.startswith("reply_ticket_"):
        try:
            ticket_id = int(data.replace("reply_ticket_", ""))
            user = update.effective_user
            telegram_id = user.id
            token = get_user_token(telegram_id)
            user_data = api.get_user_data(token) if token else None
            user_lang = get_user_lang(user_data, context, token)
            
            await query.edit_message_text(
                f"💬 **{get_text('reply_to_ticket', user_lang)}**\n\n"
                f"{get_text('ticket', user_lang)} #{ticket_id}\n\n"
                f"{get_text('send_your_reply', user_lang)}:",
                parse_mode="Markdown"
            )
            context.user_data["waiting_for_ticket_reply"] = True
            context.user_data["reply_ticket_id"] = ticket_id
        except (ValueError, IndexError):
            user = update.effective_user
            telegram_id = user.id
            token = get_user_token(telegram_id)
            user_data = api.get_user_data(token) if token else None
            user_lang = get_user_lang(user_data, context, token)
            await query.answer(f"❌ {get_text('invalid_ticket_id', user_lang)}")
    
    elif data == "register_user":
        await register_user(update, context)
    
    elif data.startswith("reg_lang_"):
        lang = data.replace("reg_lang_", "")
        await register_select_language(update, context, lang)
    
    elif data.startswith("reg_currency_"):
        currency = data.replace("reg_currency_", "")
        await register_select_currency(update, context, currency)
    
    elif data == "settings":
        await show_settings(update, context)
    
    elif data.startswith("set_currency_"):
        currency = data.replace("set_currency_", "")
        await set_currency(update, context, currency)
    
    elif data.startswith("set_lang_"):
        lang = data.replace("set_lang_", "")
        await set_language(update, context, lang)
    
    elif data == "select_language":
        await set_language(update, context)


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать настройки (валюта и язык)"""
    query = update.callback_query
    if not query:
        return
    
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        await query.answer("❌ Ошибка авторизации")
        return
    
    user_data = api.get_user_data(token)
    if not user_data:
        await query.answer("❌ Не удалось загрузить данные")
        return
    
    # Получаем язык и валюту с правильными ключами
    user_lang = get_user_lang(user_data, context, token)
    current_currency = user_data.get("preferred_currency") or user_data.get("preferredCurrency") or "uah"
    
    logger.debug(f"Settings: lang={user_lang}, currency={current_currency}")
    
    text = f"⚙️ **{get_text('settings', user_lang)}**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Текущие настройки в современном стиле
    currency_names = {"uah": "₴ UAH", "rub": "₽ RUB", "usd": "$ USD"}
    currency_display = currency_names.get(current_currency, 'UAH')
    
    text += f"💱 **{get_text('currency', user_lang)}**\n"
    text += f"{currency_display}\n\n"
    
    lang_names = {"ru": "🇷🇺 Русский", "ua": "🇺🇦 Українська", "en": "🇬🇧 English", "cn": "🇨🇳 中文"}
    lang_display = lang_names.get(user_lang, 'Русский')
    
    text += f"🌐 **{get_text('language', user_lang)}**\n"
    text += f"{lang_display}\n\n"
    
    text += f"📝 {get_text('select_currency', user_lang)}\n"
    
    keyboard = [
        [
            InlineKeyboardButton("₴ UAH" + (" ✓" if current_currency == "uah" else ""), callback_data="set_currency_uah"),
            InlineKeyboardButton("₽ RUB" + (" ✓" if current_currency == "rub" else ""), callback_data="set_currency_rub")
        ],
        [
            InlineKeyboardButton("$ USD" + (" ✓" if current_currency == "usd" else ""), callback_data="set_currency_usd")
        ],
        [
            InlineKeyboardButton(f"🌐 {get_text('language', user_lang)}", callback_data="select_language")
        ],
        [
            InlineKeyboardButton(f"🔙 {get_text('back', user_lang)}", callback_data="main_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(text):
        text_clean = clean_markdown_for_cards(text)
        try:
            await query.edit_message_text(
                text_clean,
                reply_markup=reply_markup
            )
        except Exception as e:
            # Обрабатываем ошибку "Message is not modified"
            if "not modified" in str(e).lower():
                pass
            else:
                logger.error(f"Error editing message in show_settings: {e}")
                try:
                    await query.message.reply_text(
                        text_clean,
                        reply_markup=reply_markup
                    )
                except:
                    pass
    else:
        try:
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            # Обрабатываем ошибку "Message is not modified"
            if "not modified" in str(e).lower():
                pass
            else:
                logger.error(f"Error editing message in show_settings: {e}")
                try:
                    await query.message.reply_text(
                        clean_markdown_for_cards(text),
                        reply_markup=reply_markup
                    )
                except:
                    pass


async def set_currency(update: Update, context: ContextTypes.DEFAULT_TYPE, currency: str):
    """Установить валюту"""
    query = update.callback_query
    if not query:
        return
    
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        await query.answer("❌ Ошибка авторизации")
        return
    
    if currency not in ["uah", "rub", "usd"]:
        await query.answer("❌ Неверная валюта")
        return
    
    # Проверяем текущую валюту
    user_data = api.get_user_data(token)
    current_currency = user_data.get("preferred_currency", "uah") if user_data else "uah"
    
    if current_currency == currency:
        await query.answer("ℹ️ Эта валюта уже выбрана", show_alert=False)
        return
    
    # Сохраняем валюту
    result = api.save_settings(token, currency=currency)
    
    logger.info(f"Currency save result: {result}")
    
    if result.get("success"):
        await query.answer("✅ Валюта изменена", show_alert=False)
        # Возвращаемся к настройкам (данные обновятся автоматически из БД)
        try:
            await show_settings(update, context)
        except Exception as e:
            # Если ошибка "Message is not modified", просто игнорируем
            if "not modified" not in str(e).lower():
                logger.error(f"Error updating settings: {e}")
                await query.answer("✅ Валюта изменена", show_alert=False)
    else:
        error_msg = result.get("message", "Ошибка сохранения валюты")
        logger.error(f"Failed to save currency: {error_msg}")
        await query.answer(f"❌ {error_msg}", show_alert=True)


async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str = None):
    """Показать меню выбора языка или установить язык"""
    query = update.callback_query
    if not query:
        return
    
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        await query.answer("❌ Ошибка авторизации")
        return
    
    user_data = api.get_user_data(token)
    if not user_data:
        await query.answer("❌ Не удалось загрузить данные")
        return
    
    current_lang = get_user_lang(user_data, context, token)
    
    # Если язык не указан, показываем меню выбора
    if not lang:
        text = f"🌐 **{get_text('select_language', current_lang)}**\n\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🇷🇺 Русский" + (" ✓" if current_lang == "ru" else ""), callback_data="set_lang_ru"),
                InlineKeyboardButton("🇺🇦 Українська" + (" ✓" if current_lang == "ua" else ""), callback_data="set_lang_ua")
            ],
            [
                InlineKeyboardButton("🇬🇧 English" + (" ✓" if current_lang == "en" else ""), callback_data="set_lang_en"),
                InlineKeyboardButton("🇨🇳 中文" + (" ✓" if current_lang == "cn" else ""), callback_data="set_lang_cn")
            ],
            [
                InlineKeyboardButton(f"🔙 {get_text('back', current_lang)}", callback_data="settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            # Обрабатываем ошибку "Message is not modified"
            if "not modified" in str(e).lower():
                # Игнорируем эту ошибку - сообщение уже правильное
                pass
            else:
                logger.error(f"Error editing message in set_language: {e}")
        return
    
    # Устанавливаем язык
    if lang not in ["ru", "ua", "en", "cn"]:
        await query.answer("❌ Неверный язык")
        return
    
    # Проверяем текущий язык
    if current_lang == lang:
        await query.answer("ℹ️ Этот язык уже выбран", show_alert=False)
        return
    
    # Сохраняем язык
    result = api.save_settings(token, lang=lang)
    
    logger.info(f"Language save result: {result}")
    
    if result.get("success"):
        await query.answer("✅ Язык изменен", show_alert=False)
        # Обновляем язык в context.user_data для немедленного применения
        context.user_data['user_lang'] = lang
        # Очищаем кэш user_data, чтобы при следующем запросе получить свежие данные
        if 'user_data' in context.user_data:
            del context.user_data['user_data']
        # Возвращаемся к настройкам (данные обновятся автоматически из БД)
        try:
            await show_settings(update, context)
        except Exception as e:
            # Если ошибка "Message is not modified", просто игнорируем
            if "not modified" not in str(e).lower():
                logger.error(f"Error updating settings: {e}")
                await query.answer("✅ Язык изменен", show_alert=False)
    else:
        error_msg = result.get("message", "Ошибка сохранения языка")
        logger.error(f"Failed to save language: {error_msg}")
        await query.answer(f"❌ {error_msg}", show_alert=True)


async def view_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE, ticket_id: int):
    """Просмотр тикета с сообщениями"""
    query = update.callback_query
    if not query:
        return
    
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        lang = get_user_lang(None, context, token)
        await query.answer(f"❌ {get_text('auth_error', lang)}")
        return
    
    user_data = api.get_user_data(token)
    user_lang = get_user_lang(user_data, context, token)
    
    await query.answer(f"⏳ {get_text('loading_ticket', user_lang)}...")
    
    ticket_data = api.get_ticket_messages(token, ticket_id)
    
    if not ticket_data or not ticket_data.get("messages"):
        await query.edit_message_text(
            f"❌ **{get_text('error_loading', user_lang)}**\n\n"
            f"{get_text('ticket_not_found', user_lang)} #{ticket_id}.\n"
            f"{get_text('ticket_not_exists', user_lang)}",
            parse_mode="Markdown"
        )
        return
    
    subject = ticket_data.get("subject", get_text('no_subject', user_lang))
    status = ticket_data.get("status", "OPEN")
    status_emoji = "✅" if status == "CLOSED" else "🔄"
    messages = ticket_data.get("messages", [])
    
    text = f"💬 **{get_text('ticket_view_title', user_lang)} #{ticket_id}**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"{status_emoji} **{get_text('status_label', user_lang)}:** {status}\n"
    text += f"📋 **{get_text('subject_label', user_lang)}:** {subject}\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"💬 **{get_text('messages_label', user_lang)}:**\n\n"
    
    # Показываем сообщения
    for msg in messages:
        sender_email = msg.get("sender_email", get_text('unknown', user_lang))
        sender_role = msg.get("sender_role", "USER")
        message_text = msg.get("message", "")
        created_at = msg.get("created_at", "")
        
        # Определяем, кто отправил
        if sender_role == "ADMIN":
            sender_label = f"👨‍💼 {get_text('support_label', user_lang)} ({sender_email})"
        else:
            sender_label = f"👤 {get_text('you', user_lang)}"
        
        # Форматируем дату
        try:
            if created_at:
                msg_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                date_str = msg_date.strftime('%d.%m.%Y %H:%M')
            else:
                date_str = get_text('unknown', user_lang)
        except:
            date_str = created_at
        
        text += f"**{sender_label}**\n"
        text += f"📅 {date_str}\n"
        text += f"{message_text}\n\n"
        text += "—\n\n" # Разделитель сообщений
    
    keyboard = [
        [InlineKeyboardButton(f"💬 {get_text('reply_button', user_lang)}", callback_data=f"reply_ticket_{ticket_id}")],
        [InlineKeyboardButton(f"🔙 {get_text('back_to_support', user_lang)}", callback_data="support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(text):
        text_clean = clean_markdown_for_cards(text)
        await query.edit_message_text(
            text_clean,
            reply_markup=reply_markup
        )
    else:
        # Для текста без карточек используем Markdown
        try:
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Markdown parsing error, sending without formatting: {e}")
            await query.edit_message_text(
                clean_markdown_for_cards(text),
                reply_markup=reply_markup
            )


async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать процесс регистрации - выбор языка"""
    query = update.callback_query
    if not query:
        return
    
    user = update.effective_user
    telegram_id = user.id
    
    # Проверяем, не зарегистрирован ли уже
    token = get_user_token(telegram_id)
    if token:
        lang = get_user_lang(None, context, token) if token else 'ru'
        await query.answer(f"✅ {get_text('already_registered', lang)}", show_alert=True)
        await show_status(update, context)
        return
    
    # Начинаем процесс регистрации - сначала выбор языка
    # Используем русский по умолчанию для незарегистрированных
    lang = 'ru'
    
    text = "🛡️ **StealthNET VPN**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    text += "👋 **Добро пожаловать!**\n\n"
    text += "🌐 Выберите язык интерфейса для удобной работы.\n\n"
    text += "💡 Вы сможете изменить его позже в настройках."
    
    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="reg_lang_ru"),
            InlineKeyboardButton("🇺🇦 Українська", callback_data="reg_lang_ua")
        ],
        [
            InlineKeyboardButton("🇬🇧 English", callback_data="reg_lang_en"),
            InlineKeyboardButton("🇨🇳 中文", callback_data="reg_lang_cn")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(text):
        text_clean = clean_markdown_for_cards(text)
        await query.edit_message_text(
            text_clean,
            reply_markup=reply_markup
        )
    else:
        # Для текста без карточек используем Markdown
        try:
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Markdown parsing error, sending without formatting: {e}")
            await query.edit_message_text(
                clean_markdown_for_cards(text),
                reply_markup=reply_markup
            )


async def register_select_language(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    """Выбор языка при регистрации - переход к выбору валюты"""
    query = update.callback_query
    if not query:
        return
    
    # Сохраняем выбранный язык
    context.user_data["reg_lang"] = lang
    
    lang_names = {"ru": "Русский", "ua": "Українська", "en": "English", "cn": "中文"}
    lang_name = lang_names.get(lang, "Русский")
    
    await query.answer(f"✅ Язык: {lang_name}")
    
    text = "🛡️ **StealthNET VPN**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    text += f"✅ **Язык выбран:** {lang_name}\n\n"
    text += "💱 **Выберите валюту**\n"
    text += "Для отображения цен в тарифах.\n\n"
    text += "💡 Вы сможете изменить её позже в настройках."
    
    keyboard = [
        [
            InlineKeyboardButton("₴ UAH", callback_data="reg_currency_uah"),
            InlineKeyboardButton("₽ RUB", callback_data="reg_currency_rub")
        ],
        [
            InlineKeyboardButton("$ USD", callback_data="reg_currency_usd")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(text):
        text_clean = clean_markdown_for_cards(text)
        await query.edit_message_text(
            text_clean,
            reply_markup=reply_markup
        )
    else:
        # Для текста без карточек используем Markdown
        try:
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Markdown parsing error, sending without formatting: {e}")
            await query.edit_message_text(
                clean_markdown_for_cards(text),
                reply_markup=reply_markup
            )


async def register_select_currency(update: Update, context: ContextTypes.DEFAULT_TYPE, currency: str):
    """Выбор валюты при регистрации - завершение регистрации"""
    query = update.callback_query
    if not query:
        return
    
    user = update.effective_user
    telegram_id = user.id
    telegram_username = user.username or ""
    
    # Получаем сохраненный язык
    lang = context.user_data.get("reg_lang", "ru")
    
    # Сохраняем выбранную валюту
    context.user_data["reg_currency"] = currency
    
    currency_names = {"uah": "₴ UAH", "rub": "₽ RUB", "usd": "$ USD"}
    currency_name = currency_names.get(currency, "₴ UAH")
    
    await query.answer("⏳ Регистрируем...")
    
    # Показываем выбранные настройки
    lang_names = {"ru": "Русский", "ua": "Українська", "en": "English", "cn": "中文"}
    lang_name = lang_names.get(lang, "Русский")
    
    text = "🛡️ **StealthNET VPN**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    text += "✅ **Настройки**\n"
    text += f"🌐 {lang_name}\n"
    text += f"💱 {currency_name}\n\n"
    text += "⏳ Создаем ваш аккаунт..."
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(text):
        text_clean = clean_markdown_for_cards(text)
        await query.edit_message_text(text_clean)
    else:
        try:
            await query.edit_message_text(text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Markdown parsing error, sending without formatting: {e}")
            await query.edit_message_text(clean_markdown_for_cards(text))
    
    # Проверяем, есть ли реферальный код в контексте
    ref_code = context.user_data.get("ref_code")
    
    # Регистрируем пользователя с выбранными языком и валютой
    result = api.register_user(telegram_id, telegram_username, ref_code, preferred_lang=lang, preferred_currency=currency)
    
    if not result:
        text = "❌ **Ошибка регистрации**\n\n"
        text += "Не удалось зарегистрироваться. Попробуйте позже или зарегистрируйтесь на сайте:\n"
        text += "https://panel.stealthnet.app/register"
        
        keyboard = [[InlineKeyboardButton("🔙 Попробовать снова", callback_data="register_user")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        return
    
    if result.get("message") == "User already registered":
        await query.answer("✅ Вы уже зарегистрированы!", show_alert=True)
        token = get_user_token(telegram_id)
        if token:
            await show_status(update, context)
        return
    
    # Регистрация успешна
    email = result.get("email", "")
    password = result.get("password", "")
    
    # Сохраняем язык в context для немедленного применения
    context.user_data['user_lang'] = lang
    
    # Формируем красивое сообщение об успешной регистрации
    text = "✨ **Регистрация завершена!**\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    text += "✅ **Аккаунт создан!**\n"
    text += "Ваш аккаунт успешно создан и готов к использованию!\n\n"
    
    if email and password:
        text += "🔐 **Данные для входа**\n"
        text += f"📧 `{email}`\n"
        text += f"🔑 `{password}`\n\n"
        
        text += "⚠️ **Важно!**\n"
        text += "Сохраните эти данные! Пароль больше не будет показан.\n\n"
        
        text += "🌐 Войти на сайте:\n"
        text += "https://panel.stealthnet.app\n\n"
    
    text += "🎉 Теперь вы можете использовать все функции бота!"
    
    keyboard = [
        [InlineKeyboardButton("📊 Статус подписки", callback_data="status")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(text):
        text_clean = clean_markdown_for_cards(text)
        await query.edit_message_text(
            text_clean,
            reply_markup=reply_markup
        )
    else:
        # Для текста без карточек используем Markdown
        try:
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Markdown parsing error, sending without formatting: {e}")
            await query.edit_message_text(
                clean_markdown_for_cards(text),
                reply_markup=reply_markup
            )
    
    # Сохраняем токен в кэш (если он есть)
    if result.get("token"):
        user_tokens[telegram_id] = result["token"]
    
    # Очищаем временные данные регистрации
    context.user_data.pop("reg_lang", None)
    context.user_data.pop("reg_currency", None)


async def activate_trial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Активировать триал"""
    query = update.callback_query
    if not query:
        return
    
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        lang = get_user_lang(None, context, token)
        await query.answer(f"❌ {get_text('auth_error', lang)}", show_alert=True)
        return
    
    user_data = api.get_user_data(token)
    user_lang = get_user_lang(user_data, context, token)
    
    await query.answer(f"⏳ {get_text('activating_trial', user_lang)}...")
    
    result = api.activate_trial(token)
    
    keyboard = [[InlineKeyboardButton(f"🔙 {get_text('main_menu_button', user_lang)}", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Проверяем результат активации
    if result and "message" in result:
        message_text = result.get("message", "").lower()
        # Проверяем на успех: "trial activated", "активирован", "успешно" и т.д.
        if ("trial" in message_text and "activated" in message_text) or \
           "активирован" in message_text or \
           "успешно" in message_text or \
           result.get("success", False):
            text = f"✅ **{get_text('trial_activated_title', user_lang)}**\n"
            text += "━━━━━━━━━━━━━━━━━━━━\n\n"
            text += f"{get_text('trial_days_received', user_lang)}\n"
            text += f"{get_text('enjoy_vpn', user_lang)}"
            
            try:
                await query.edit_message_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Markdown parsing error in activate_trial, sending without formatting: {e}")
                await query.edit_message_text(
                    clean_markdown_for_cards(text),
                    reply_markup=reply_markup
                )
        else:
            # Если сообщение есть, но не об успехе - показываем его
            message = result.get("message", get_text('error_activating_trial', user_lang))
            await query.edit_message_text(
                f"❌ **{get_text('error', user_lang)}**\n\n{message}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    elif result and result.get("success", False):
        # Если есть поле success = True
        text = f"✅ **{get_text('trial_activated_title', user_lang)}**\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"{get_text('trial_days_received', user_lang)}\n"
        text += f"{get_text('enjoy_vpn', user_lang)}"
        
        try:
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Markdown parsing error in activate_trial, sending without formatting: {e}")
            await query.edit_message_text(
                clean_markdown_for_cards(text),
                reply_markup=reply_markup
            )
    else:
        # Если result пустой или нет нужных полей
        error_message = result.get("message", get_text('failed_activate_trial', user_lang)) if result else get_text('failed_activate_trial', user_lang)
        await query.edit_message_text(
            f"❌ **{get_text('error', user_lang)}**\n\n{error_message}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE, tariff_id: Optional[int] = None):
    """Выбрать тариф и способ оплаты"""
    query = update.callback_query
    if not query:
        return
    
    if not tariff_id:
        # Получаем из callback_data
        if query.data:
            try:
                tariff_id = int(query.data.split("_")[1])
            except (ValueError, IndexError):
                await query.answer("❌ Ошибка: неверный ID тарифа", show_alert=True)
                return
        else:
            return
    
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        await query.answer("❌ Ошибка авторизации", show_alert=True)
        return
    
    # Получаем информацию о тарифе
    tariffs = api.get_tariffs()
    tariff = next((t for t in tariffs if t.get("id") == tariff_id), None)
    
    if not tariff:
        await query.answer("❌ Тариф не найден", show_alert=True)
        return
    
    user_data = api.get_user_data(token)
    currency = user_data.get("preferred_currency", "uah") if user_data else "uah"
    user_lang = get_user_lang(user_data, context, token)
    
    currency_map = {
        "uah": {"field": "price_uah", "symbol": "₴"},
        "rub": {"field": "price_rub", "symbol": "₽"},
        "usd": {"field": "price_usd", "symbol": "$"}
    }
    currency_config = currency_map.get(currency, currency_map["uah"])
    price = tariff.get(currency_config["field"], 0)
    
    text = f"💎 **{get_text('tariff_selected', user_lang)}:** {tariff.get('name', get_text('unknown', user_lang))}\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"💰 **{get_text('price_label', user_lang)}:** {price:.0f} {currency_config['symbol']}\n"
    text += f"📅 **{get_text('duration_label', user_lang)}:** {tariff.get('duration_days', 0)} {get_text('days', user_lang)}\n\n"
    text += f"**{get_text('payment_methods', user_lang)}**:"
    
    # Получаем доступные способы оплаты из API
    available_methods = api.get_available_payment_methods()
    
    # Маппинг названий способов оплаты
    payment_names = {
        'crystalpay': '💳 CrystalPay',
        'heleket': '₿ Heleket',
        'yookassa': '💳 YooKassa',
        'platega': '💳 Platega',
        'mulenpay': '💳 Mulenpay',
        'urlpay': '💳 UrlPay',
        'telegram_stars': '⭐ Telegram Stars',
        'monobank': '💳 Monobank',
        'btcpayserver': '₿ BTCPayServer'
    }
    
    keyboard = []
    row = []
    
    # Добавляем только доступные способы оплаты
    for method in available_methods:
        if method in payment_names:
            row.append(InlineKeyboardButton(
                payment_names[method],
                callback_data=f"pay_{tariff_id}_{method}"
            ))
            # По 2 кнопки в ряд
            if len(row) == 2:
                keyboard.append(row)
                row = []
    
    # Добавляем оставшиеся кнопки
    if row:
        keyboard.append(row)
    
    # Если нет доступных способов оплаты
    if not keyboard:
        text += f"\n\n❌ {get_text('no_payment_methods', user_lang)}"
    
    keyboard.append([
        InlineKeyboardButton(f"🔙 {get_text('back_to_tariffs', user_lang)}", callback_data="tariffs")
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если текст содержит карточки, убираем Markdown-форматирование
    if has_cards(text):
        text_clean = clean_markdown_for_cards(text)
        await update.callback_query.edit_message_text(
            text_clean,
            reply_markup=reply_markup
        )
    else:
        # Для текста без карточек используем Markdown
        try:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Markdown parsing error in show_tariffs, sending without formatting: {e}")
            await update.callback_query.edit_message_text(
                clean_markdown_for_cards(text),
                reply_markup=reply_markup
            )


async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, tariff_id: int, provider: str):
    """Обработать создание платежа"""
    query = update.callback_query
    if not query:
        return
    
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        lang = get_user_lang(None, context, token)
        await query.answer(f"❌ {get_text('auth_error', lang)}")
        return
    
    user_data = api.get_user_data(token)
    user_lang = get_user_lang(user_data, context, token)
    
    await query.answer(f"⏳ {get_text('creating_payment', user_lang)}...")
    
    result = api.create_payment(token, tariff_id, provider)
    
    if result.get("payment_url"):
        payment_url = result["payment_url"]
        text = f"💳 **{get_text('payment_created_title', user_lang)}**\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"{get_text('go_to_payment_text', user_lang)}:\n\n"
        text += f"`{payment_url}`\n\n"
        text += f"{get_text('after_payment', user_lang)}"
        
        keyboard = [
            [InlineKeyboardButton(f"💳 {get_text('go_to_payment_button', user_lang)}", url=payment_url)],
            [InlineKeyboardButton(f"🔙 {get_text('main_menu_button', user_lang)}", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Markdown parsing error in handle_payment, sending without formatting: {e}")
            await query.edit_message_text(
                clean_markdown_for_cards(text),
                reply_markup=reply_markup
            )
    else:
        message = result.get("message", get_text('error_creating_payment', user_lang))
        keyboard = [[InlineKeyboardButton(f"🔙 {get_text('back_to_tariffs', user_lang)}", callback_data="tariffs")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❌ **{get_text('error', user_lang)}**\n\n{message}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


def main():
    """Главная функция запуска бота"""
    # Создаем приложение
    application = Application.builder().token(CLIENT_BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    
    # Обработчик платежей (должен быть ПЕРЕД общим button_callback, так как он более специфичный)
    async def payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if query and query.data and query.data.startswith("pay_"):
            try:
                parts = query.data.split("_")
                if len(parts) >= 3:
                    tariff_id = int(parts[1])
                    provider = "_".join(parts[2:])
                    await handle_payment(update, context, tariff_id, provider)
                    return  # Важно: возвращаемся, чтобы не обрабатывать дальше
                else:
                    await query.answer("❌ Неверный формат данных платежа")
            except (ValueError, IndexError) as e:
                logger.error(f"Payment callback error: {e}")
                await query.answer("❌ Ошибка обработки платежа", show_alert=True)
    
    # Регистрируем обработчик платежей ПЕРВЫМ (более специфичный паттерн)
    application.add_handler(CallbackQueryHandler(payment_callback, pattern="^pay_"))
    
    # Регистрируем общий обработчик callback кнопок ПОСЛЕ специфичных
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик текстовых сообщений (для создания тикетов)
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        if update.message and update.message.text:
            user_data = context.user_data
            
            if user_data.get("waiting_for_ticket_subject"):
                # Сохраняем тему и просим сообщение
                user_data["ticket_subject"] = update.message.text
                user_data["waiting_for_ticket_subject"] = False
                user_data["waiting_for_ticket_message"] = True
                
                await update.message.reply_text(
                    "💬 **Создание тикета**\n\n"
                    "Тема сохранена. Теперь отправьте текст сообщения:",
                    parse_mode="Markdown"
                )
            
            elif user_data.get("waiting_for_ticket_message"):
                # Создаем тикет
                subject = user_data.get("ticket_subject", "Без темы")
                message = update.message.text
                
                telegram_id = update.effective_user.id
                token = get_user_token(telegram_id)
                
                if token:
                    result = api.create_support_ticket(token, subject, message)
                    
                    # API возвращает {"message": "Created", "ticket_id": nt.id} со статусом 201
                    # Проверяем оба варианта
                    ticket_id = result.get("ticket_id") if result else None
                    if not ticket_id and result and result.get("message") == "Created":
                        # Пытаемся получить ticket_id из другого поля
                        ticket_id = result.get("id")
                    
                    if ticket_id:
                        await update.message.reply_text(
                            f"✅ **Тикет создан!**\n\n"
                            f"Номер тикета: #{ticket_id}\n"
                            f"Тема: {subject}\n\n"
                            f"Мы ответим вам в ближайшее время.\n\n"
                            f"Вы можете просмотреть тикет в разделе поддержки.",
                            parse_mode="Markdown"
                        )
                    else:
                        error_msg = result.get("message", "Ошибка создания тикета") if result else "Ошибка создания тикета"
                        await update.message.reply_text(
                            f"❌ **Ошибка**\n\n{error_msg}",
                            parse_mode="Markdown"
                        )
                else:
                    await update.message.reply_text(
                        "❌ Ошибка авторизации. Используйте /start для повторной авторизации."
                    )
                
                # Очищаем состояние
                user_data.pop("ticket_subject", None)
                user_data.pop("waiting_for_ticket_message", None)
            
            elif user_data.get("waiting_for_ticket_reply"):
                # Отвечаем на тикет
                ticket_id = user_data.get("reply_ticket_id")
                message = update.message.text
                
                telegram_id = update.effective_user.id
                token = get_user_token(telegram_id)
                
                if token and ticket_id:
                    result = api.reply_to_ticket(token, ticket_id, message)
                    
                    if result.get("id") or result.get("success"):
                        await update.message.reply_text(
                            f"✅ **Ответ отправлен!**\n\n"
                            f"Тикет #{ticket_id}\n\n"
                            f"Ваш ответ был добавлен в тикет.",
                            parse_mode="Markdown"
                        )
                    else:
                        error_msg = result.get("message", "Ошибка отправки ответа") if result else "Ошибка отправки ответа"
                        await update.message.reply_text(
                            f"❌ **Ошибка**\n\n{error_msg}",
                            parse_mode="Markdown"
                        )
                else:
                    await update.message.reply_text(
                        "❌ Ошибка авторизации. Используйте /start для повторной авторизации."
                    )
                
                # Очищаем состояние
                user_data.pop("waiting_for_ticket_reply", None)
                user_data.pop("reply_ticket_id", None)
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    logger.info("Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

