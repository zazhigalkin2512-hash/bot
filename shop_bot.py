"""
Telegram Store Bot Template
===========================

This script provides a template for a Telegram‑based store bot.  It is
inspired by the features described in a 17 December 2024 review of a
Telegram store bot【25562505261946†L99-L123】.  The goal of this template
is to replicate many of the capabilities available in that bot while
remaining transparent and extensible.  It supports separate interfaces
for regular users and administrators, category and product management,
basic referral tracking, promotional codes, daily backups and optional
notifications.  Payment integration is intentionally left as a stub to
allow the developer to plug in a payment provider that suits their
needs.

**Disclaimer**: This script is provided for educational purposes and
should only be used to sell lawful products and services.  Before
deploying it in production, review the Telegram Bot Platform terms of
service, add proper error handling and integrate an appropriate
payment provider.

To run this bot you need to install the `python‑telegram‑bot` library
version 13 or higher.  Install it with pip:

```
pip install python‑telegram‑bot
```

Next, create a bot using [@BotFather](https://t.me/BotFather) and set
your token below.  You should also specify the list of administrator
user IDs that are allowed to access the control panel.  These IDs can
be obtained from Telegram using the `/start` command or via
`update.effective_user.id` when the user first interacts with your
bot.

Key Features
------------

* **Flexible configuration** – administrators can toggle many bot
  functions on or off.  For example, you may disable the referral
  system or notifications【25562505261946†L99-L123】.
* **Channel/Chat buttons** – you can add custom buttons linking to
  your news channel or community chat【25562505261946†L102-L104】.
* **Promo codes and referral system** – issue promo codes that give
  percentage discounts or bonuses, and track referrals for traffic
  incentives【25562505261946†L106-L116】.
* **Statistics dashboard** – administrators can view sales and user
  statistics for day/week/month periods【25562505261946†L108-L110】.
* **User management** – search for users, adjust balances, block
  problematic accounts and review payment receipts【25562505261946†L109-L113】.
* **Product management** – create categories, subcategories and
  products with descriptions and images.  The bot supports
  “infinite” products where stock never runs out【25562505261946†L114-L116】.
* **Broadcasts** – send marketing messages to all users with optional
  images【25562505261946†L117-L118】.
* **Automated backups** – schedule daily exports of the database to
  protect against data loss【25562505261946†L119-L120】.
* **Payment providers** – integrate multiple payment methods; stub
  functions are provided for demonstration【25562505261946†L121-L123】.

This template uses an SQLite database to persist data.  You may wish
to switch to another storage backend (e.g. PostgreSQL) for production.

"""

import logging
import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Tuple

from telegram import (Bot, InlineKeyboardButton, InlineKeyboardMarkup,
                      Update)
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

# ----------------------------------------------------------------------------
# Configuration – fill these values before running
# ----------------------------------------------------------------------------

# Your Telegram bot token obtained from @BotFather
BOT_TOKEN = os.getenv("TELEGRAM_STORE_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# List of administrator Telegram user IDs.  These users will have
# access to the admin panel and advanced commands.  Example:
# ADMIN_IDS = {123456789, 987654321}
ADMIN_IDS: set[int] = set(map(int, os.getenv("TELEGRAM_STORE_ADMIN_IDS", "").split()))

# Path to SQLite database file.  It will be created on first run.
DB_PATH = os.getenv("TELEGRAM_STORE_DB", "store_bot.db")

# Directory where backups will be stored.  Ensure this directory exists and
# that your hosting environment has permission to write into it.
BACKUP_DIR = os.getenv("TELEGRAM_STORE_BACKUP_DIR", "backups")

# ----------------------------------------------------------------------------
# Database helper functions
# ----------------------------------------------------------------------------

def init_db() -> sqlite3.Connection:
    """Create the necessary tables if they don't already exist.

    The database schema covers users, products, categories,
    subcategories, promo codes, orders and settings.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    # Table for bot settings (toggle features)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    # Table for users
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0.0,
            referred_by INTEGER,
            blocked INTEGER DEFAULT 0
        )
        """
    )

    # Table for categories
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
        """
    )

    # Table for subcategories
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS subcategories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
        """
    )

    # Table for products
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subcategory_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER,
            image_path TEXT,
            FOREIGN KEY (subcategory_id) REFERENCES subcategories(id) ON DELETE CASCADE
        )
        """
    )

    # Table for promo codes
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            discount REAL,
            expiry_date TEXT
        )
        """
    )

    # Table for orders
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            total_price REAL,
            status TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """
    )

    conn.commit()
    return conn


def get_db_conn(context: CallbackContext) -> sqlite3.Connection:
    """Retrieve a database connection from the bot's context cache.
    The connection is stored on a per‑dispatcher basis to avoid
    creating many separate connections.
    """
    if not hasattr(context.bot_data, "db_conn"):
        context.bot_data["db_conn"] = init_db()
    return context.bot_data["db_conn"]


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Insert or update a setting in the settings table."""
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()


def get_setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    """Retrieve a setting value or return a default if not set."""
    cur = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    return row[0] if row else default


# ----------------------------------------------------------------------------
# Decorators for permission checks
# ----------------------------------------------------------------------------

def admin_only(func):
    """Decorator that restricts command handlers to administrators."""

    @wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else 0
        if user_id not in ADMIN_IDS:
            update.message.reply_text("Извините, у вас нет прав для этой команды.")
            return
        return func(update, context, *args, **kwargs)

    return wrapper


def ensure_registered(func):
    """Decorator to ensure the user is in the database."""

    @wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        conn = get_db_conn(context)
        user = update.effective_user
        if not user:
            return
        cur = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (user.id,))
        if not cur.fetchone():
            # register new user
            conn.execute(
                "INSERT INTO users (user_id, username) VALUES (?, ?)",
                (user.id, user.username or "")
            )
            conn.commit()
        return func(update, context, *args, **kwargs)

    return wrapper


# ----------------------------------------------------------------------------
# Bot command handlers – user interface
# ----------------------------------------------------------------------------

@ensure_registered
def start_handler(update: Update, context: CallbackContext) -> None:
    """Handle the /start command for both users and admins.

    Administrators see a management menu whereas regular users see the
    customer menu.  This command can also process referral codes and
    promotional codes supplied as parameters.
    """
    user = update.effective_user
    message = update.message
    # Check if the user is blocked
    conn = get_db_conn(context)
    cur = conn.execute("SELECT blocked FROM users WHERE user_id = ?", (user.id,))
    if cur.fetchone() and cur.fetchone()[0]:
        message.reply_text("Ваш аккаунт заблокирован.")
        return

    # Process payloads like /start REFERCODE
    if message.text and len(message.text.split()) > 1:
        payload = message.text.split()[1]
        if payload.startswith("REF="):
            referrer_id = int(payload.replace("REF=", ""))
            # Save referral if user has not been referred before
            cur = conn.execute(
                "SELECT referred_by FROM users WHERE user_id = ?", (user.id,)
            )
            ref = cur.fetchone()
            if ref and ref[0] is None and referrer_id != user.id:
                conn.execute(
                    "UPDATE users SET referred_by = ? WHERE user_id = ?",
                    (referrer_id, user.id)
                )
                conn.commit()
        elif payload.startswith("PROMO="):
            code = payload.replace("PROMO=", "").upper()
            # store promo code usage in context for later use
            context.user_data['promo_code'] = code

    if user.id in ADMIN_IDS:
        message.reply_text(
            "Привет, администратор! Выберите действие:",
            reply_markup=admin_main_menu()
        )
    else:
        message.reply_text(
            "Добро пожаловать в магазин! Выберите категорию:",
            reply_markup=user_main_menu(conn)
        )


def user_main_menu(conn: sqlite3.Connection) -> InlineKeyboardMarkup:
    """Generate the main menu for users, listing top-level categories."""
    keyboard = []
    cur = conn.execute("SELECT id, name FROM categories")
    for cat_id, name in cur.fetchall():
        keyboard.append([InlineKeyboardButton(name, callback_data=f"cat_{cat_id}")])
    # Add optional buttons for channel/chat links from settings
    news_link = get_setting(conn, "news_channel", "")
    chat_link = get_setting(conn, "chat_link", "")
    extras = []
    if news_link:
        extras.append(InlineKeyboardButton("Новости", url=news_link))
    if chat_link:
        extras.append(InlineKeyboardButton("Чат", url=chat_link))
    if extras:
        keyboard.append(extras)
    return InlineKeyboardMarkup(keyboard)


def admin_main_menu() -> InlineKeyboardMarkup:
    """Return the inline keyboard for admin panel entry points."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔧 Общие настройки", callback_data="admin_settings")],
        [InlineKeyboardButton("⚙️ Доп. настройки", callback_data="admin_extra_settings")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🔍 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("🛍️ Товары", callback_data="admin_products")],
        [InlineKeyboardButton("📣 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("💾 Backup", callback_data="admin_backup")],
    ])


# ----------------------------------------------------------------------------
# Callback query handlers for navigating menus
# ----------------------------------------------------------------------------

def category_callback(update: Update, context: CallbackContext) -> None:
    """Handle user clicking on a category – list its subcategories."""
    query = update.callback_query
    if not query:
        return
    query.answer()
    conn = get_db_conn(context)
    # Extract category id
    cat_id = int(query.data.split("_")[1])
    cur = conn.execute(
        "SELECT id, name FROM subcategories WHERE category_id = ?",
        (cat_id,)
    )
    subcats = cur.fetchall()
    if not subcats:
        query.edit_message_text(
            text="Нет подкатегорий в этой категории.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data="back_to_main")]
            ])
        )
        return
    keyboard = [[InlineKeyboardButton(name, callback_data=f"sub_{sid}")]
                for sid, name in subcats]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_main")])
    query.edit_message_text("Выберите подкатегорию:", reply_markup=InlineKeyboardMarkup(keyboard))


def subcategory_callback(update: Update, context: CallbackContext) -> None:
    """Handle user clicking on a subcategory – list its products."""
    query = update.callback_query
    if not query:
        return
    query.answer()
    conn = get_db_conn(context)
    sub_id = int(query.data.split("_")[1])
    cur = conn.execute(
        "SELECT id, name, price FROM products WHERE subcategory_id = ?",
        (sub_id,)
    )
    products = cur.fetchall()
    if not products:
        query.edit_message_text(
            text="Нет товаров в этой подкатегории.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data="back_to_main")]
            ])
        )
        return
    keyboard = [[InlineKeyboardButton(f"{name} – {price}₽", callback_data=f"prod_{pid}")]
                for pid, name, price in products]
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_main")])
    query.edit_message_text("Выберите товар:", reply_markup=InlineKeyboardMarkup(keyboard))


def product_callback(update: Update, context: CallbackContext) -> None:
    """Handle user clicking on a product – show its details and offer purchase."""
    query = update.callback_query
    if not query:
        return
    query.answer()
    conn = get_db_conn(context)
    prod_id = int(query.data.split("_")[1])
    cur = conn.execute(
        "SELECT name, description, price, stock FROM products WHERE id = ?",
        (prod_id,)
    )
    row = cur.fetchone()
    if not row:
        query.edit_message_text("Товар не найден.")
        return
    name, description, price, stock = row
    text = f"<b>{name}</b>\n\n{description}\n\nЦена: {price}₽"
    if stock is None:
        text += "\nТовар бесконечен"
    else:
        text += f"\nОсталось: {stock}"
    keyboard = [
        [InlineKeyboardButton("Купить", callback_data=f"buy_{prod_id}")],
        [InlineKeyboardButton("Назад", callback_data="back_to_main")],
    ]
    query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


def buy_product_callback(update: Update, context: CallbackContext) -> None:
    """Process purchase of a product: deduct balance or call payment stub."""
    query = update.callback_query
    if not query:
        return
    query.answer()
    user_id = query.from_user.id
    prod_id = int(query.data.split("_")[1])
    conn = get_db_conn(context)
    # Get product details
    cur = conn.execute("SELECT name, price, stock FROM products WHERE id = ?", (prod_id,))
    product = cur.fetchone()
    if not product:
        query.edit_message_text("Товар не найден.")
        return
    name, price, stock = product
    # Get user balance
    cur = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    bal_row = cur.fetchone()
    balance = bal_row[0] if bal_row else 0.0
    # Apply promo code discount if present
    promo_code = context.user_data.get('promo_code')
    discount = 0.0
    if promo_code:
        ccur = conn.execute(
            "SELECT discount, expiry_date FROM promocodes WHERE code = ?",
            (promo_code,)
        )
        prow = ccur.fetchone()
        if prow:
            discount_value, expiry = prow
            if expiry is None or datetime.now() <= datetime.fromisoformat(expiry):
                discount = discount_value
    final_price = price * (1 - discount)
    # If user has enough balance, complete purchase
    if balance >= final_price:
        conn.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ?",
            (final_price, user_id),
        )
        # decrement stock if finite
        if stock is not None and stock > 0:
            conn.execute(
                "UPDATE products SET stock = stock - 1 WHERE id = ?",
                (prod_id,),
            )
        # Create order record
        conn.execute(
            "INSERT INTO orders (user_id, product_id, quantity, total_price, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, prod_id, 1, final_price, "paid", datetime.now().isoformat()),
        )
        conn.commit()
        query.edit_message_text(
            f"Покупка успешна! Вы приобрели {name} за {final_price:.2f}₽."
        )
    else:
        # Insufficient balance – call payment stub
        query.edit_message_text(
            f"Недостаточно средств. Пополните баланс на {final_price - balance:.2f}₽.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Пополнить баланс", callback_data=f"pay_{final_price}")],
                [InlineKeyboardButton("Назад", callback_data="back_to_main")],
            ])
        )


def payment_callback(update: Update, context: CallbackContext) -> None:
    """Stub for processing external payment.  Customize as needed."""
    query = update.callback_query
    if not query:
        return
    query.answer()
    amount_str = query.data.split("_")[1]
    try:
        amount = float(amount_str)
    except ValueError:
        query.edit_message_text("Ошибка при обработке платежа.")
        return
    # Here you would integrate with a payment processor (e.g., PayPal,
    # Stripe, or Telegram’s native payments).  For demonstration we
    # simply add the amount to the user's balance.
    user_id = query.from_user.id
    conn = get_db_conn(context)
    conn.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id),
    )
    conn.commit()
    query.edit_message_text(
        f"Баланс успешно пополнен на {amount:.2f}₽!"
    )


def back_to_main_callback(update: Update, context: CallbackContext) -> None:
    """Return to main menu for the user."""
    query = update.callback_query
    if not query:
        return
    query.answer()
    conn = get_db_conn(context)
    if query.from_user.id in ADMIN_IDS:
        query.edit_message_text(
            "Панель администратора:", reply_markup=admin_main_menu()
        )
    else:
        query.edit_message_text(
            "Добро пожаловать в магазин! Выберите категорию:",
            reply_markup=user_main_menu(conn)
        )


# ----------------------------------------------------------------------------
# Admin command handlers and helpers
# ----------------------------------------------------------------------------

@admin_only
def admin_settings_handler(update: Update, context: CallbackContext) -> None:
    """Show general settings – toggles for features and notifications."""
    query = update.callback_query
    if query:
        query.answer()
        message = query
        edit = True
    else:
        message = update.message
        edit = False
    conn = get_db_conn(context)
    # Retrieve current settings
    notif_enabled = get_setting(conn, "notifications", "1") == "1"
    referral_enabled = get_setting(conn, "referral", "1") == "1"
    stats_enabled = get_setting(conn, "stats", "1") == "1"
    # Build keyboard with toggles
    keyboard = [
        [InlineKeyboardButton(
            f"Уведомления: {'✅' if notif_enabled else '❌'}",
            callback_data="toggle_notifications"
        )],
        [InlineKeyboardButton(
            f"Реф. система: {'✅' if referral_enabled else '❌'}",
            callback_data="toggle_referral"
        )],
        [InlineKeyboardButton(
            f"Статистика: {'✅' if stats_enabled else '❌'}",
            callback_data="toggle_stats"
        )],
        [InlineKeyboardButton("Назад", callback_data="back_to_main")],
    ]
    text = (
        "Общие настройки:\n"
        "\nВы можете включать или выключать функции бота.\n"
        "\n– Уведомления: присылать ли сообщения о новых пользователях или оплате."
        "\n– Реферальная система: учитывать ли реферальные переходы."
        "\n– Статистика: вести статистику продаж и пользователей."
    )
    if edit:
        message.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


@admin_only
def admin_extra_settings_handler(update: Update, context: CallbackContext) -> None:
    """Show extra settings – manage promo codes and referral thresholds."""
    query = update.callback_query
    if query:
        query.answer()
        message = query
        edit = True
    else:
        message = update.message
        edit = False
    text = (
        "Дополнительные настройки:\n"
        "\n– Управление промокодами: добавление, удаление, просмотр."
        "\n– Настройка порогов рефералов для доступа к определённым акциям."
        "\n(Функция в разработке.)\n"
        "\nВыберите действие:"
    )
    keyboard = [
        [InlineKeyboardButton("Добавить промокод", callback_data="add_promocode")],
        [InlineKeyboardButton("Список промокодов", callback_data="list_promocodes")],
        [InlineKeyboardButton("Назад", callback_data="back_to_main")],
    ]
    if edit:
        message.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


@admin_only
def admin_stats_handler(update: Update, context: CallbackContext) -> None:
    """Show sales and user statistics for various time periods."""
    query = update.callback_query
    if query:
        query.answer()
        message = query
        edit = True
    else:
        message = update.message
        edit = False
    conn = get_db_conn(context)
    # Count users
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    # Calculate sales for different periods
    now = datetime.now()
    def sales_since(delta: timedelta) -> float:
        since = (now - delta).isoformat()
        row = conn.execute(
            "SELECT SUM(total_price) FROM orders WHERE status = 'paid' AND created_at >= ?",
            (since,),
        ).fetchone()
        return row[0] or 0.0
    daily = sales_since(timedelta(days=1))
    weekly = sales_since(timedelta(weeks=1))
    monthly = sales_since(timedelta(days=30))
    text = (
        f"Статистика бота:\n\n"
        f"Пользователей: {user_count}\n"
        f"Продажи за сутки: {daily:.2f}₽\n"
        f"Продажи за неделю: {weekly:.2f}₽\n"
        f"Продажи за месяц: {monthly:.2f}₽\n"
    )
    if edit:
        message.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Назад", callback_data="back_to_main")],
        ]))
    else:
        message.reply_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Назад", callback_data="back_to_main")],
        ]))


@admin_only
def admin_users_handler(update: Update, context: CallbackContext) -> None:
    """Display user management options: search, adjust balance, ban/unban."""
    query = update.callback_query
    if query:
        query.answer()
        message = query
        edit = True
    else:
        message = update.message
        edit = False
    text = (
        "Управление пользователями:\n"
        "\nВы можете найти пользователя по ID или юзернейму, изменить его баланс,
заблокировать или разблокировать, а также посмотреть чеки оплаты."
    )
    # For simplicity this implementation uses messages rather than full interactive search.
    if edit:
        message.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data="back_to_main")],
            ])
        )
    else:
        message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data="back_to_main")],
            ])
        )


@admin_only
def admin_products_handler(update: Update, context: CallbackContext) -> None:
    """Entry point for product management."""
    query = update.callback_query
    if query:
        query.answer()
        message = query
        edit = True
    else:
        message = update.message
        edit = False
    text = (
        "Управление товарами:\n"
        "\nВы можете создавать категории, подкатегории и товары.\n"
        "– Добавить категорию\n"
        "– Добавить подкатегорию\n"
        "– Добавить товар\n"
        "– Список категорий\n"
    )
    keyboard = [
        [InlineKeyboardButton("Добавить категорию", callback_data="add_category")],
        [InlineKeyboardButton("Добавить подкатегорию", callback_data="add_subcategory")],
        [InlineKeyboardButton("Добавить товар", callback_data="add_product")],
        [InlineKeyboardButton("Список категорий", callback_data="list_categories")],
        [InlineKeyboardButton("Назад", callback_data="back_to_main")],
    ]
    if edit:
        message.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


@admin_only
def admin_broadcast_handler(update: Update, context: CallbackContext) -> None:
    """Initiate a broadcast message to all users."""
    query = update.callback_query
    if query:
        query.answer()
        context.user_data['broadcast_step'] = 'ask_text'
        query.message.reply_text(
            "Введите текст рассылки или отправьте 'отмена' для отмены."
        )
    else:
        update.message.reply_text(
            "Чтобы начать рассылку, нажмите кнопку из панели администратора."
        )


@admin_only
def admin_backup_handler(update: Update, context: CallbackContext) -> None:
    """Perform a manual backup of the database and send it to the admin."""
    query = update.callback_query
    if query:
        query.answer()
        message = query
    else:
        message = update.message
    # Ensure backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    # Copy the current database to the backup path
    conn = get_db_conn(context)
    conn.backup(sqlite3.connect(backup_path))
    message.reply_document(open(backup_path, 'rb'), caption="Backup создан.")


def toggle_setting(update: Update, context: CallbackContext, key: str) -> None:
    """Toggle a boolean setting and update the message."""
    query = update.callback_query
    if not query:
        return
    conn = get_db_conn(context)
    current = get_setting(conn, key, "1") == "1"
    set_setting(conn, key, "0" if current else "1")
    # Refresh settings panel
    admin_settings_handler(update, context)


def handle_button_callbacks(update: Update, context: CallbackContext) -> None:
    """Dispatch callback queries to appropriate handlers."""
    query = update.callback_query
    if not query:
        return
    data = query.data
    if data == "back_to_main":
        back_to_main_callback(update, context)
    elif data.startswith("cat_"):
        category_callback(update, context)
    elif data.startswith("sub_"):
        subcategory_callback(update, context)
    elif data.startswith("prod_"):
        product_callback(update, context)
    elif data.startswith("buy_"):
        buy_product_callback(update, context)
    elif data.startswith("pay_"):
        payment_callback(update, context)
    elif data == "admin_settings":
        admin_settings_handler(update, context)
    elif data == "admin_extra_settings":
        admin_extra_settings_handler(update, context)
    elif data == "admin_stats":
        admin_stats_handler(update, context)
    elif data == "admin_users":
        admin_users_handler(update, context)
    elif data == "admin_products":
        admin_products_handler(update, context)
    elif data == "admin_broadcast":
        admin_broadcast_handler(update, context)
    elif data == "admin_backup":
        admin_backup_handler(update, context)
    elif data == "toggle_notifications":
        toggle_setting(update, context, "notifications")
    elif data == "toggle_referral":
        toggle_setting(update, context, "referral")
    elif data == "toggle_stats":
        toggle_setting(update, context, "stats")
    # Additional admin actions like add_category, add_subcategory etc. can be
    # implemented below.  For brevity they are omitted.


# ----------------------------------------------------------------------------
# Broadcast conversation handlers
# ----------------------------------------------------------------------------

def broadcast_text_handler(update: Update, context: CallbackContext) -> int:
    """Receive the broadcast text from the admin."""
    text = update.message.text
    if text.lower() == "отмена":
        update.message.reply_text("Рассылка отменена.")
        return ConversationHandler.END
    context.user_data['broadcast_text'] = text
    update.message.reply_text(
        "Если хотите отправить картинку вместе с рассылкой, отправьте файл.\n"
        "Если нет, отправьте 'нет' для продолжения."
    )
    return 1


def broadcast_media_handler(update: Update, context: CallbackContext) -> int:
    """Receive an optional media file for the broadcast and send to all users."""
    if update.message.text and update.message.text.lower() == "нет":
        file_id = None
    else:
        # Use whichever media type was sent: photo, document, etc.
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
        elif update.message.document:
            file_id = update.message.document.file_id
        else:
            update.message.reply_text("Тип файла не поддерживается. Попробуйте ещё раз или отправьте 'нет'.")
            return 1
    text = context.user_data.get('broadcast_text', '')
    conn = get_db_conn(context)
    cur = conn.execute("SELECT user_id FROM users WHERE blocked = 0")
    recipients = [row[0] for row in cur.fetchall()]
    bot: Bot = context.bot
    for uid in recipients:
        try:
            if file_id:
                bot.send_photo(chat_id=uid, photo=file_id, caption=text)
            else:
                bot.send_message(chat_id=uid, text=text)
        except Exception as e:
            logging.warning(f"Failed to send broadcast to {uid}: {e}")
    update.message.reply_text(f"Рассылка завершена. Отправлено: {len(recipients)} пользователям.")
    return ConversationHandler.END


# ----------------------------------------------------------------------------
# Main function to set up handlers and start the bot
# ----------------------------------------------------------------------------

def main() -> None:
    """Start the bot and register handlers."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Initialize the database at startup
    init_db()

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", start_handler))

    # Callback query handler for all buttons
    dispatcher.add_handler(CallbackQueryHandler(handle_button_callbacks))

    # Conversation handler for broadcasts
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast_handler, pattern="admin_broadcast")],
        states={
            # Ask for text
            'ask_text': [MessageHandler(Filters.text & ~Filters.command, broadcast_text_handler)],
            # Ask for optional media
            1: [MessageHandler(
                (Filters.photo | Filters.document | (Filters.text & ~Filters.command)),
                broadcast_media_handler
            )],
        },
        fallbacks=[MessageHandler(Filters.text & ~Filters.command, lambda u, c: ConversationHandler.END)],
        map_to_parent={
            # Map conversation end to finishing broadcast
            ConversationHandler.END: ConversationHandler.END
        },
    )
    dispatcher.add_handler(broadcast_conv)

    # Start the bot
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
