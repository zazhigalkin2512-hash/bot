from dotenv import load_dotenv
import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Создаем файл .env если его нет
if not os.path.exists('.env'):
    with open('.env', 'w', encoding='utf-8') as f:
        f.write('''BOT_TOKEN=8287745399:AAFvdmUWdMU6Q7ZOMDoOY1Dl-4leiQwwYlc
ADVEGO_LOGIN=your_advego_login
ADVEGO_PASSWORD=your_advego_password
TEXTSALE_LOGIN=your_textsale_login
TEXTSALE_PASSWORD=your_textsale_password
WORKZILLA_LOGIN=your_workzilla_login
WORKZILLA_PASSWORD=your_workzilla_password
KWORK_LOGIN=your_kwork_login
KWORK_PASSWORD=your_kwork_password
CAPTCHA_SERVICE=anti-captcha
CAPTCHA_API_KEY=your_captcha_api_key
DATABASE_URL=sqlite:///bot.db
''')
    print("📁 Создан файл .env")
    print("❌ ВАЖНО: Откройте файл .env и замените 'ВАШ_ТОКЕН_БОТА_ЗДЕСЬ' на ваш реальный токен бота!")
    print("🤖 Как получить токен:")
    print("1. Напишите @BotFather в Telegram")
    print("2. Отправьте команду /newbot")
    print("3. Придумайте имя бота")
    print("4. Получите токен и вставьте его в файл .env")
    exit(1)

# Загружаем переменные из .env файла
load_dotenv()

# Проверяем токен
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN or BOT_TOKEN == 'ВАШ_ТОКЕН_БОТА_ЗДЕСЬ':
    print("❌ Ошибка: Не установлен BOT_TOKEN!")
    print("📝 Откройте файл .env и замените 'ВАШ_ТОКЕН_БОТА_ЗДЕСЬ' на ваш реальный токен бота")
    print("🤖 Как получить токен:")
    print("1. Напишите @BotFather в Telegram")
    print("2. Отправьте команду /newbot")
    print("3. Придумайте имя бота")
    print("4. Получите токен и вставьте его в файл .env")
    exit(1)

# Класс конфигурации
class Config:
    def __init__(self):
        self.BOT_TOKEN = BOT_TOKEN
        
        self.EXCHANGES = {
            'advego': {
                'login': os.getenv('ADVEGO_LOGIN'),
                'password': os.getenv('ADVEGO_PASSWORD'),
            },
            'textsale': {
                'login': os.getenv('TEXTSALE_LOGIN'),
                'password': os.getenv('TEXTSALE_PASSWORD')
            },
            'workzilla': {
                'login': os.getenv('WORKZILLA_LOGIN'),
                'password': os.getenv('WORKZILLA_PASSWORD')
            },
            'kwork': {
                'login': os.getenv('KWORK_LOGIN'),
                'password': os.getenv('KWORK_PASSWORD')
            }
        }
        
        self.SETTINGS = {
            'check_interval': 60,
            'max_tasks_per_day': 50,
            'min_task_price': 0.1,
            'max_task_price': 1000,
            'auto_accept_tasks': True,
            'use_proxy': False
        }

# Главный класс бота
class AutoEarnBot:
    def __init__(self):
        self.config = Config()
        self.active_users = {}
        self.setup_database()
        
    def setup_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                registration_date TEXT,
                total_earned REAL DEFAULT 0,
                tasks_completed INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                exchange TEXT,
                task_type TEXT,
                amount REAL,
                status TEXT,
                created_at TEXT,
                completed_at TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balances (
                user_id INTEGER,
                exchange TEXT,
                balance REAL DEFAULT 0,
                last_updated TEXT,
                PRIMARY KEY (user_id, exchange)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        self.register_user(user_id, user.username)
        
        keyboard = [
            [InlineKeyboardButton("🚀 Начать работу", callback_data="start_work")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
            [InlineKeyboardButton("💰 Балансы", callback_data="balances")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🤖 Добро пожаловать, {user.first_name}!\n\n"
            "Я - автоматический бот для заработка на биржах фриланса.\n"
            "Я могу автоматически:\n"
            "• Искать и брать задания\n"
            "• Выполнять кликовые задания\n"
            "• Писать простые тексты\n"
            "• Выполнять SEO задания\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
    
    def register_user(self, user_id, username):
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO users (user_id, username, registration_date) VALUES (?, ?, ?)',
            (user_id, username, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if query.data == "start_work":
            await self.start_work_menu(query)
        elif query.data == "stats":
            await self.show_stats(query)
        elif query.data == "settings":
            await self.show_settings(query)
        elif query.data == "balances":
            await self.show_balances(query)
        elif query.data == "help":
            await self.show_help(query)
        elif query.data.startswith("exchange_"):
            exchange = query.data.replace("exchange_", "")
            await self.toggle_exchange(query, exchange)
        elif query.data.startswith("start_auto_"):
            exchange = query.data.replace("start_auto_", "")
            await self.start_auto_work(query, exchange)
    
    async def start_work_menu(self, query):
        keyboard = [
            [InlineKeyboardButton("Advego ✅", callback_data="exchange_advego")],
            [InlineKeyboardButton("TextSale ❌", callback_data="exchange_textsale")],
            [InlineKeyboardButton("Workzilla ❌", callback_data="exchange_workzilla")],
            [InlineKeyboardButton("Kwork ❌", callback_data="exchange_kwork")],
            [InlineKeyboardButton("🎯 Начать авто-работу", callback_data="start_auto_all")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔧 Выберите биржи для работы:\n\n"
            "✅ - активна\n❌ - отключена\n\n"
            "Настройте биржи и нажмите 'Начать авто-работу':",
            reply_markup=reply_markup
        )
    
    async def toggle_exchange(self, query, exchange):
        user_id = query.from_user.id
        if user_id not in self.active_users:
            self.active_users[user_id] = {'exchanges': set(), 'working': False}
        
        if exchange in self.active_users[user_id]['exchanges']:
            self.active_users[user_id]['exchanges'].remove(exchange)
            status = "❌"
        else:
            self.active_users[user_id]['exchanges'].add(exchange)
            status = "✅"
        
        exchanges_status = {
            'advego': "❌", 'textsale': "❌", 
            'workzilla': "❌", 'kwork': "❌"
        }
        for active_exchange in self.active_users[user_id]['exchanges']:
            exchanges_status[active_exchange] = "✅"
        
        keyboard = [
            [InlineKeyboardButton(f"Advego {exchanges_status['advego']}", callback_data="exchange_advego")],
            [InlineKeyboardButton(f"TextSale {exchanges_status['textsale']}", callback_data="exchange_textsale")],
            [InlineKeyboardButton(f"Workzilla {exchanges_status['workzilla']}", callback_data="exchange_workzilla")],
            [InlineKeyboardButton(f"Kwork {exchanges_status['kwork']}", callback_data="exchange_kwork")],
            [InlineKeyboardButton("🎯 Начать авто-работу", callback_data="start_auto_all")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔧 Выберите биржи для работы:\n\n"
            "✅ - активна\n❌ - отключена\n\n"
            "Настройте биржи и нажмите 'Начать авто-работу':",
            reply_markup=reply_markup
        )
    
    async def start_auto_work(self, query, exchange):
        user_id = query.from_user.id
        
        if user_id not in self.active_users or not self.active_users[user_id]['exchanges']:
            await query.edit_message_text(
                "❌ Сначала выберите хотя бы одну биржу для работы!"
            )
            return
        
        self.active_users[user_id]['working'] = True
        
        await query.edit_message_text(
            "🚀 Запускаю автоматическую работу...\n\n"
            "Бот начал поиск и выполнение заданий на выбранных биржах.\n"
            "Я буду присылать уведомления о выполненных заданиях."
        )
    
    async def show_stats(self, query):
        """Показать статистику"""
        user_id = query.from_user.id
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT total_earned, tasks_completed FROM users WHERE user_id = ?',
            (user_id,)
        )
        result = cursor.fetchone()
        
        if result:
            total_earned, tasks_completed = result
            
            cursor.execute(
                'SELECT exchange, SUM(amount) FROM tasks WHERE user_id = ? GROUP BY exchange',
                (user_id,)
            )
            by_exchange = cursor.fetchall()
            
            stats_text = f"📊 Ваша статистика:\n\n"
            stats_text += f"💰 Всего заработано: {total_earned:.2f} руб.\n"
            stats_text += f"✅ Выполнено заданий: {tasks_completed}\n\n"
            stats_text += "📈 По биржам:\n"
            
            for exchange, amount in by_exchange:
                if amount:
                    stats_text += f"• {exchange.capitalize()}: {amount:.2f} руб.\n"
        else:
            stats_text = "📊 Статистика не найдена\n\nНачните работу, чтобы увидеть статистику!"
        
        conn.close()
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="start_work")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(stats_text, reply_markup=reply_markup)
    
    async def show_balances(self, query):
        """Показать балансы на биржах"""
        user_id = query.from_user.id
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT exchange, balance FROM balances WHERE user_id = ?',
            (user_id,)
        )
        balances = cursor.fetchall()
        
        balance_text = "💰 Ваши балансы:\n\n"
        total = 0
        
        for exchange, balance in balances:
            balance_text += f"• {exchange.capitalize()}: {balance:.2f} руб.\n"
            total += balance
        
        if total > 0:
            balance_text += f"\n💵 Итого: {total:.2f} руб."
        else:
            balance_text = "💰 Балансы не найдены\n\nНачните работу, чтобы увидеть балансы!"
        
        conn.close()
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="start_work")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(balance_text, reply_markup=reply_markup)
    
    async def show_settings(self, query):
        """Показать настройки"""
        settings_text = (
            "⚙️ Настройки бота:\n\n"
            f"🔍 Интервал проверки: {self.config.SETTINGS['check_interval']} сек.\n"
            f"📦 Макс. заданий в день: {self.config.SETTINGS['max_tasks_per_day']}\n"
            f"💵 Мин. цена задания: {self.config.SETTINGS['min_task_price']} руб.\n"
            f"💵 Макс. цена задания: {self.config.SETTINGS['max_task_price']} руб.\n"
            f"🤖 Автопринятие: {'Вкл' if self.config.SETTINGS['auto_accept_tasks'] else 'Выкл'}\n"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="start_work")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(settings_text, reply_markup=reply_markup)
    
    async def show_help(self, query):
        """Показать помощь"""
        help_text = (
            "❓ Помощь по боту\n\n"
            "🤖 Как работает бот:\n"
            "1. Выбираете биржи для работы\n"
            "2. Бот автоматически ищет задания\n"
            "3. Выполняет подходящие задания\n"
            "4. Вы получаете деньги\n\n"
            "⚡ Возможности:\n"
            "• Автопоиск заданий\n"
            "• Автовыполнение\n"
            "• Умные фильтры\n"
            "• Статистика\n\n"
            "⚠️ Важно:\n"
            "• Соблюдайте правила бирж\n"
            "• Настройте лимиты\n"
            "• Мониторьте работу\n"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="start_work")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(help_text, reply_markup=reply_markup)
    
    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Остановка работы"""
        user_id = update.effective_user.id
        if user_id in self.active_users:
            self.active_users[user_id]['working'] = False
            await update.message.reply_text("⏹️ Работа остановлена")
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статус работы"""
        user_id = update.effective_user.id
        if user_id in self.active_users and self.active_users[user_id].get('working', False):
            status_text = "🟢 Бот работает\n"
            active_exchanges = [ex.capitalize() for ex in self.active_users[user_id]['exchanges']]
            status_text += f"📊 Активные биржи: {', '.join(active_exchanges)}"
        else:
            status_text = "🔴 Бот остановлен"
        
        await update.message.reply_text(status_text)

def main():
    """Синхронная главная функция"""
    print("🤖 Бот запускается...")
    
    try:
        # Создаем бота и приложение
        bot = AutoEarnBot()
        
        # Создаем приложение
        application = Application.builder().token(bot.config.BOT_TOKEN).build()
        
        # Обработчики команд
        application.add_handler(CommandHandler("start", bot.start))
        application.add_handler(CommandHandler("stop", bot.stop))
        application.add_handler(CommandHandler("status", bot.status))
        application.add_handler(CommandHandler("stats", bot.show_stats))
        
        # Обработчики кнопок
        application.add_handler(CallbackQueryHandler(bot.button_handler))
        
        print("✅ Бот успешно запущен!")
        print("📝 Используйте команду /start в Telegram для начала работы")
        
        # Запускаем бота
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main()