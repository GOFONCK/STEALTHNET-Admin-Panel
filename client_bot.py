#!/usr/bin/env python3
"""
Telegram Bot для клиентов StealthNET VPN
Предоставляет функционал Dashboard через Telegram интерфейс
"""

import os
import logging
import requests
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
    
    def register_user(self, telegram_id: int, telegram_username: str = "", ref_code: str = None) -> Optional[dict]:
        """Зарегистрировать пользователя через бота"""
        try:
            response = self.session.post(
                f"{self.api_url}/api/bot/register",
                json={
                    "telegram_id": telegram_id,
                    "telegram_username": telegram_username,
                    "ref_code": ref_code
                },
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
    
    def get_user_data(self, token: str) -> Optional[dict]:
        """Получить данные пользователя"""
        try:
            response = self.session.get(
                f"{self.api_url}/api/client/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response") or data
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
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Ошибка создания тикета: {e}")
        return {"success": False, "message": "Ошибка создания тикета"}


# Инициализация API клиента
api = ClientBotAPI(FLASK_API_URL)

# Кэш токенов пользователей (в продакшене лучше использовать Redis)
user_tokens = {}


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
        keyboard = [
            [
                InlineKeyboardButton("✅ Зарегистрироваться", callback_data="register_user")
            ],
            [
                InlineKeyboardButton("🌐 Зарегистрироваться на сайте", url="https://panel.stealthnet.app/register")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 Добро пожаловать в StealthNET VPN Bot!\n\n"
            "❌ Вы еще не зарегистрированы в системе.\n\n"
            "📝 Вы можете зарегистрироваться прямо здесь в боте или на сайте.\n\n"
            "💡 После регистрации вы получите логин и пароль для входа на сайте.",
            reply_markup=reply_markup
        )
        return
    
    # Получаем данные пользователя
    user_data = api.get_user_data(token)
    
    if not user_data:
        await update.message.reply_text(
            "❌ Не удалось загрузить данные пользователя."
        )
        return
    
    # Получаем данные для входа
    credentials = api.get_credentials(telegram_id)
    
    # Формируем приветственное сообщение с подробной информацией
    welcome_text = f"👋 Добро пожаловать, {user.first_name}!\n\n"
    welcome_text += "🤖 **StealthNET VPN Bot**\n"
    welcome_text += "="*30 + "\n\n"
    
    # Статус подписки
    is_active = user_data.get("activeInternalSquads", [])
    expire_at = user_data.get("expireAt")
    subscription_url = user_data.get("subscriptionUrl", "")
    used_traffic = user_data.get("usedTrafficBytes", 0)
    traffic_limit = user_data.get("trafficLimitBytes", 0)
    
    welcome_text += "📊 **Статус подписки:**\n"
    if is_active and expire_at:
        expire_date = datetime.fromisoformat(expire_at.replace('Z', '+00:00'))
        days_left = (expire_date - datetime.now(expire_date.tzinfo)).days
        
        welcome_text += f"✅ Активна\n"
        welcome_text += f"📅 Истекает: {expire_date.strftime('%d.%m.%Y %H:%M')}\n"
        welcome_text += f"⏰ Осталось дней: {days_left}\n\n"
        
        # Трафик
        welcome_text += "📊 **Трафик:**\n"
        if traffic_limit == 0:
            welcome_text += "♾️ Безлимитный\n"
        else:
            used_gb = used_traffic / (1024 ** 3)
            limit_gb = traffic_limit / (1024 ** 3)
            percentage = (used_traffic / traffic_limit * 100) if traffic_limit > 0 else 0
            welcome_text += f"📥 {used_gb:.2f} GB / {limit_gb:.2f} GB ({percentage:.1f}%)\n"
        welcome_text += "\n"
    else:
        welcome_text += "❌ Не активна\n"
        welcome_text += "💡 Активируйте триал или выберите тариф\n\n"
    
    # Данные для входа на сайте
    welcome_text += "🔐 **Данные для входа на сайте:**\n"
    if credentials and credentials.get("email"):
        welcome_text += f"📧 Логин: `{credentials['email']}`\n"
        if credentials.get("password"):
            welcome_text += f"🔑 Пароль: `{credentials['password']}`\n"
        elif credentials.get("has_password"):
            welcome_text += "🔑 Пароль: Установлен (недоступен)\n"
        else:
            welcome_text += "⚠️ Пароль не установлен\n"
    else:
        welcome_text += "❌ Данные не найдены\n"
    
    # Кнопки главного меню
    keyboard = []
    
    # Кнопка подключения (если есть активная подписка и ссылка)
    if is_active and subscription_url:
        keyboard.append([
            InlineKeyboardButton("🚀 Подключиться", url=subscription_url)
        ])
    
    keyboard.extend([
        [
            InlineKeyboardButton("📊 Статус подписки", callback_data="status"),
            InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")
        ],
        [
            InlineKeyboardButton("🌐 Серверы", callback_data="servers"),
            InlineKeyboardButton("🎁 Рефералы", callback_data="referrals")
        ],
        [
            InlineKeyboardButton("💬 Поддержка", callback_data="support")
        ]
    ])
    
    # Добавляем Web App кнопку, если URL настроен
    if MINIAPP_URL and MINIAPP_URL.startswith("https://"):
        keyboard.append([
            InlineKeyboardButton("📱 Кабинет", web_app=WebAppInfo(url=MINIAPP_URL))
        ])
    else:
        logger.warning(f"MINIAPP_URL не настроен или не HTTPS: {MINIAPP_URL}")
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
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
        await update.callback_query.answer("❌ Ошибка авторизации")
        return
    
    user_data = api.get_user_data(token)
    if not user_data:
        await update.callback_query.answer("❌ Не удалось загрузить данные")
        return
    
    # Формируем сообщение со статусом
    is_active = user_data.get("activeInternalSquads", [])
    expire_at = user_data.get("expireAt")
    used_traffic = user_data.get("usedTrafficBytes", 0)
    traffic_limit = user_data.get("trafficLimitBytes", 0)
    subscription_url = user_data.get("subscriptionUrl", "")
    
    status_text = "📊 **Статус подписки**\n\n"
    
    if is_active and expire_at:
        expire_date = datetime.fromisoformat(expire_at.replace('Z', '+00:00'))
        days_left = (expire_date - datetime.now(expire_date.tzinfo)).days
        
        status_text += f"✅ **Статус:** Активна\n"
        status_text += f"📅 **Истекает:** {expire_date.strftime('%d.%m.%Y %H:%M')}\n"
        status_text += f"⏰ **Осталось дней:** {days_left}\n"
        
        if subscription_url:
            status_text += f"\n🔗 **Ссылка подключения:**\n`{subscription_url}`\n"
    else:
        status_text += "❌ **Статус:** Не активна\n"
        status_text += "💡 Активируйте триал или выберите тариф\n"
    
    # Трафик
    status_text += "\n📊 **Использование трафика:**\n"
    if traffic_limit == 0:
        status_text += "♾️ Безлимитный трафик\n"
    else:
        used_gb = used_traffic / (1024 ** 3)
        limit_gb = traffic_limit / (1024 ** 3)
        percentage = (used_traffic / traffic_limit * 100) if traffic_limit > 0 else 0
        status_text += f"📥 Использовано: {used_gb:.2f} GB / {limit_gb:.2f} GB ({percentage:.1f}%)\n"
    
    # Добавляем информацию о логине и пароле для входа на сайте
    status_text += "\n" + "="*30 + "\n"
    status_text += "🔐 **Данные для входа на сайте**\n\n"
    
    credentials = api.get_credentials(telegram_id)
    if credentials and credentials.get("email"):
        status_text += f"📧 **Логин (Email):**\n`{credentials['email']}`\n\n"
        if credentials.get("password"):
            status_text += f"🔑 **Пароль:**\n`{credentials['password']}`\n\n"
            status_text += "💡 Используйте этот логин и пароль для входа на сайте\n"
            status_text += "🌐 https://panel.stealthnet.app\n"
        elif credentials.get("has_password"):
            status_text += "🔑 **Пароль:** Установлен (недоступен)\n"
            status_text += "💡 Используйте этот логин и пароль для входа на сайте\n"
            status_text += "🌐 https://panel.stealthnet.app\n"
        else:
            status_text += "⚠️ Пароль не установлен\n"
    else:
        status_text += "❌ Данные для входа не найдены\n"
    
    # Кнопки действий
    keyboard = []
    
    # Кнопка подключения (если есть активная подписка и ссылка)
    if is_active and subscription_url:
        keyboard.append([
            InlineKeyboardButton("🚀 Подключиться", url=subscription_url)
        ])
    
    if not is_active or not expire_at:
        keyboard.append([InlineKeyboardButton("🎁 Активировать триал", callback_data="activate_trial")])
    keyboard.append([
        InlineKeyboardButton("💎 Выбрать тариф", callback_data="tariffs"),
        InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
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
    text = "💎 **Выберите тип тарифа**\n\n"
    
    # Показываем краткую информацию о каждом типе
    if basic_tariffs:
        min_price = min(t.get(currency_config["field"], 0) for t in basic_tariffs)
        text += f"📦 **Базовый**\n"
        text += f"   От {min_price:.0f} {symbol}\n"
        text += f"   Доступно вариантов: {len(basic_tariffs)}\n\n"
    
    if pro_tariffs:
        min_price = min(t.get(currency_config["field"], 0) for t in pro_tariffs)
        text += f"⭐ **Премиум**\n"
        text += f"   От {min_price:.0f} {symbol}\n"
        text += f"   Доступно вариантов: {len(pro_tariffs)}\n\n"
    
    if elite_tariffs:
        min_price = min(t.get(currency_config["field"], 0) for t in elite_tariffs)
        text += f"👑 **Элитный**\n"
        text += f"   От {min_price:.0f} {symbol}\n"
        text += f"   Доступно вариантов: {len(elite_tariffs)}\n\n"
    
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
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
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
    text = f"{tier_name} **тарифы**\n\n"
    text += "Выберите длительность подписки:\n\n"
    
    # Показываем список тарифов
    for tariff in tier_tariffs:
        name = tariff.get("name", f"{tariff.get('duration_days', 0)} дней")
        price = tariff.get(price_field, 0)
        duration = tariff.get("duration_days", 0)
        per_day = price / duration if duration > 0 else price
        text += f"• {name}\n"
        text += f"  💰 {price:.0f} {symbol} ({per_day:.2f} {symbol}/день)\n\n"
    
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
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
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
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
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
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
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
    
    referral_code = user_data.get("referral_code", "")
    referral_link = f"https://panel.stealthnet.app/register?ref={referral_code}" if referral_code else ""
    
    text = "🎁 **Реферальная программа**\n\n"
    text += "Приглашайте друзей и получайте бонусы!\n\n"
    
    if referral_code:
        text += f"🔗 **Ваша реферальная ссылка:**\n`{referral_link}`\n\n"
        text += f"📝 **Ваш код:** `{referral_code}`\n"
    else:
        text += "❌ Реферальный код не найден"
    
    keyboard = [
        [InlineKeyboardButton("📋 Копировать ссылку", callback_data=f"copy_ref_{referral_code}")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать поддержку"""
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        await update.callback_query.answer("❌ Ошибка авторизации")
        return
    
    tickets = api.get_support_tickets(token)
    
    text = "💬 **Поддержка**\n\n"
    
    if tickets:
        text += f"📋 **Ваши тикеты:** ({len(tickets)})\n\n"
        for ticket in tickets[:5]:
            status_emoji = "✅" if ticket.get("status") == "CLOSED" else "🔄"
            text += f"{status_emoji} Тикет #{ticket.get('id')}: {ticket.get('subject', 'Без темы')}\n"
    else:
        text += "У вас пока нет тикетов.\n"
    
    text += "\nВыберите действие:"
    
    keyboard = [
        [InlineKeyboardButton("➕ Создать тикет", callback_data="create_ticket")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "main_menu":
        # Возвращаемся к главному меню с полной информацией
        user = update.effective_user
        telegram_id = user.id
        
        token = get_user_token(telegram_id)
        if token:
            user_data = api.get_user_data(token)
            credentials = api.get_credentials(telegram_id)
            
            if user_data:
                welcome_text = f"👋 Главное меню\n\n"
                welcome_text += "="*30 + "\n\n"
                
                # Статус подписки
                is_active = user_data.get("activeInternalSquads", [])
                expire_at = user_data.get("expireAt")
                subscription_url = user_data.get("subscriptionUrl", "")
                used_traffic = user_data.get("usedTrafficBytes", 0)
                traffic_limit = user_data.get("trafficLimitBytes", 0)
                
                welcome_text += "📊 **Статус подписки:**\n"
                if is_active and expire_at:
                    expire_date = datetime.fromisoformat(expire_at.replace('Z', '+00:00'))
                    days_left = (expire_date - datetime.now(expire_date.tzinfo)).days
                    
                    welcome_text += f"✅ Активна\n"
                    welcome_text += f"📅 Истекает: {expire_date.strftime('%d.%m.%Y %H:%M')}\n"
                    welcome_text += f"⏰ Осталось дней: {days_left}\n\n"
                    
                    # Трафик
                    welcome_text += "📊 **Трафик:**\n"
                    if traffic_limit == 0:
                        welcome_text += "♾️ Безлимитный\n"
                    else:
                        used_gb = used_traffic / (1024 ** 3)
                        limit_gb = traffic_limit / (1024 ** 3)
                        percentage = (used_traffic / traffic_limit * 100) if traffic_limit > 0 else 0
                        welcome_text += f"📥 {used_gb:.2f} GB / {limit_gb:.2f} GB ({percentage:.1f}%)\n"
                    welcome_text += "\n"
                else:
                    welcome_text += "❌ Не активна\n\n"
                
                # Данные для входа
                welcome_text += "🔐 **Данные для входа:**\n"
                if credentials and credentials.get("email"):
                    welcome_text += f"📧 Логин: `{credentials['email']}`\n"
                    if credentials.get("password"):
                        welcome_text += f"🔑 Пароль: `{credentials['password']}`\n"
                    elif credentials.get("has_password"):
                        welcome_text += "🔑 Пароль: Установлен (недоступен)\n"
                
                keyboard = []
                
                # Кнопка подключения
                if is_active and subscription_url:
                    keyboard.append([
                        InlineKeyboardButton("🚀 Подключиться", url=subscription_url)
                    ])
                
                keyboard.extend([
                    [
                        InlineKeyboardButton("📊 Статус подписки", callback_data="status"),
                        InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")
                    ],
                    [
                        InlineKeyboardButton("🌐 Серверы", callback_data="servers"),
                        InlineKeyboardButton("🎁 Рефералы", callback_data="referrals")
                    ],
                    [
                        InlineKeyboardButton("💬 Поддержка", callback_data="support")
                    ]
                ])
                
                # Web App кнопка
                if MINIAPP_URL and MINIAPP_URL.startswith("https://"):
                    keyboard.append([
                        InlineKeyboardButton("📱 Кабинет", web_app=WebAppInfo(url=MINIAPP_URL))
                    ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
                return
        
        # Fallback если не удалось загрузить данные
        welcome_text = f"👋 Главное меню\n\n"
        welcome_text += "Выберите раздел:"
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Статус подписки", callback_data="status"),
                InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")
            ],
            [
                InlineKeyboardButton("🌐 Серверы", callback_data="servers"),
                InlineKeyboardButton("🎁 Рефералы", callback_data="referrals")
            ],
            [
                InlineKeyboardButton("💬 Поддержка", callback_data="support")
            ]
        ]
        
        if MINIAPP_URL and MINIAPP_URL.startswith("https://"):
            keyboard.append([
                InlineKeyboardButton("📱 Кабинет", web_app=WebAppInfo(url=MINIAPP_URL))
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
        referral_link = f"https://panel.stealthnet.app/register?ref={referral_code}"
        await query.answer(f"Ссылка скопирована: {referral_link}", show_alert=False)
    
    elif data == "create_ticket":
        await query.edit_message_text(
            "💬 **Создание тикета**\n\n"
            "Отправьте тему тикета в следующем сообщении:",
            parse_mode="Markdown"
        )
        context.user_data["waiting_for_ticket_subject"] = True
    
    elif data == "register_user":
        await register_user(update, context)


async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Зарегистрировать пользователя через бота"""
    query = update.callback_query
    if not query:
        return
    
    user = update.effective_user
    telegram_id = user.id
    telegram_username = user.username or ""
    
    # Проверяем, не зарегистрирован ли уже
    token = get_user_token(telegram_id)
    if token:
        await query.answer("✅ Вы уже зарегистрированы!", show_alert=True)
        await show_status(update, context)
        return
    
    await query.answer("⏳ Регистрируем...")
    
    # Проверяем, есть ли реферальный код в контексте
    ref_code = context.user_data.get("ref_code")
    
    # Регистрируем пользователя
    result = api.register_user(telegram_id, telegram_username, ref_code)
    
    if not result:
        await query.edit_message_text(
            "❌ **Ошибка регистрации**\n\n"
            "Не удалось зарегистрироваться. Попробуйте позже или зарегистрируйтесь на сайте:\n"
            "https://panel.stealthnet.app/register",
            parse_mode="Markdown"
        )
        return
    
    if result.get("message") == "User already registered":
        await query.answer("✅ Вы уже зарегистрированы!", show_alert=True)
        # Получаем токен и показываем статус
        token = get_user_token(telegram_id)
        if token:
            await show_status(update, context)
        return
    
    # Регистрация успешна
    email = result.get("email", "")
    password = result.get("password", "")
    
    if email and password:
        success_text = (
            "✅ **Регистрация успешна!**\n\n"
            "🔐 **Ваши данные для входа на сайте:**\n\n"
            f"📧 **Логин (Email):**\n`{email}`\n\n"
            f"🔑 **Пароль:**\n`{password}`\n\n"
            "⚠️ **ВАЖНО:** Сохраните эти данные! Пароль больше не будет показан.\n\n"
            "🌐 Войти на сайте: https://panel.stealthnet.app\n\n"
            "Теперь вы можете использовать все функции бота!"
        )
    else:
        success_text = (
            "✅ **Регистрация успешна!**\n\n"
            "Теперь вы можете использовать все функции бота!"
        )
    
    keyboard = [
        [InlineKeyboardButton("📊 Статус подписки", callback_data="status")],
        [InlineKeyboardButton("💎 Тарифы", callback_data="tariffs")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        success_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    
    # Сохраняем токен в кэш (если он есть)
    if result.get("token"):
        # Обновляем кэш токенов
        user_tokens[telegram_id] = result["token"]


async def activate_trial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Активировать триал"""
    query = update.callback_query
    if not query:
        return
    
    user = update.effective_user
    telegram_id = user.id
    
    token = get_user_token(telegram_id)
    if not token:
        await query.answer("❌ Ошибка авторизации", show_alert=True)
        return
    
    await query.answer("⏳ Активируем триал...")
    
    result = api.activate_trial(token)
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Проверяем результат активации
    if result and "message" in result:
        message_text = result.get("message", "").lower()
        # Проверяем на успех: "trial activated", "активирован", "успешно" и т.д.
        if ("trial" in message_text and "activated" in message_text) or \
           "активирован" in message_text or \
           "успешно" in message_text or \
           result.get("success", False):
            await query.edit_message_text(
                "✅ **Триал активирован!**\n\n"
                "Вы получили 3 дня премиум доступа.\n"
                "Наслаждайтесь VPN без ограничений!",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            # Если сообщение есть, но не об успехе - показываем его
            message = result.get("message", "Ошибка активации триала")
            await query.edit_message_text(
                f"❌ **Ошибка**\n\n{message}",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    elif result and result.get("success", False):
        # Если есть поле success = True
        await query.edit_message_text(
            "✅ **Триал активирован!**\n\n"
            "Вы получили 3 дня премиум доступа.\n"
            "Наслаждайтесь VPN без ограничений!",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        # Если result пустой или нет нужных полей
        error_message = result.get("message", "Не удалось активировать триал. Попробуйте позже.") if result else "Не удалось активировать триал. Попробуйте позже."
        await query.edit_message_text(
            f"❌ **Ошибка**\n\n{error_message}",
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
    
    currency_map = {
        "uah": {"field": "price_uah", "symbol": "₴"},
        "rub": {"field": "price_rub", "symbol": "₽"},
        "usd": {"field": "price_usd", "symbol": "$"}
    }
    currency_config = currency_map.get(currency, currency_map["uah"])
    price = tariff.get(currency_config["field"], 0)
    
    text = f"💎 **Выбран тариф:** {tariff.get('name', 'Неизвестно')}\n\n"
    text += f"💰 **Цена:** {price:.0f} {currency_config['symbol']}\n"
    text += f"📅 **Длительность:** {tariff.get('duration_days', 0)} дней\n\n"
    text += "Выберите способ оплаты:"
    
    keyboard = [
        [
            InlineKeyboardButton("💳 CrystalPay", callback_data=f"pay_{tariff_id}_crystalpay"),
            InlineKeyboardButton("₿ Heleket", callback_data=f"pay_{tariff_id}_heleket")
        ],
        [
            InlineKeyboardButton("💳 YooKassa", callback_data=f"pay_{tariff_id}_yookassa")
        ],
        [
            InlineKeyboardButton("⭐ Telegram Stars", callback_data=f"pay_{tariff_id}_telegram_stars")
        ],
        [
            InlineKeyboardButton("🔙 Назад к тарифам", callback_data="tariffs")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
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
        await query.answer("❌ Ошибка авторизации")
        return
    
    await query.answer("⏳ Создаем платеж...")
    
    result = api.create_payment(token, tariff_id, provider)
    
    if result.get("payment_url"):
        payment_url = result["payment_url"]
        text = f"💳 **Платеж создан**\n\n"
        text += f"Перейдите по ссылке для оплаты:\n\n"
        text += f"После успешной оплаты подписка будет активирована автоматически."
        
        keyboard = [
            [InlineKeyboardButton("💳 Перейти к оплате", url=payment_url)],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        message = result.get("message", "Ошибка создания платежа")
        keyboard = [[InlineKeyboardButton("🔙 Назад к тарифам", callback_data="tariffs")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❌ **Ошибка**\n\n{message}",
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
    
    # Регистрируем обработчик callback кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик платежей (должен быть перед общим button_callback)
    async def payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if query and query.data and query.data.startswith("pay_"):
            try:
                parts = query.data.split("_")
                if len(parts) >= 3:
                    tariff_id = int(parts[1])
                    provider = "_".join(parts[2:])
                    await handle_payment(update, context, tariff_id, provider)
                else:
                    await query.answer("❌ Неверный формат данных платежа")
            except (ValueError, IndexError) as e:
                logger.error(f"Payment callback error: {e}")
                await query.answer("❌ Ошибка обработки платежа", show_alert=True)
    
    application.add_handler(CallbackQueryHandler(payment_callback, pattern="^pay_"))
    
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
                    
                    if result.get("ticket_id"):
                        await update.message.reply_text(
                            f"✅ **Тикет создан!**\n\n"
                            f"Номер тикета: #{result.get('ticket_id')}\n"
                            f"Тема: {subject}\n\n"
                            f"Мы ответим вам в ближайшее время.",
                            parse_mode="Markdown"
                        )
                    else:
                        error_msg = result.get("message", "Ошибка создания тикета")
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
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    logger.info("Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

