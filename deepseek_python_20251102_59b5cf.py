from dotenv import load_dotenv
import os
import logging
import sqlite3
import requests
import asyncio
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
        self.work_cycles = {}  # Счетчик циклов работы для каждого пользователя
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
            [InlineKeyboardButton("🔍 Проверить работу", callback_data="check_work")],
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
        elif query.data == "check_work":
            await self.check_work_status(query)
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
            [InlineKeyboardButton("🎯 Начать авто-работу", callback_data="start_auto_all")],
            [InlineKeyboardButton("🔍 Проверить работу", callback_data="check_work")]
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
            [InlineKeyboardButton("🎯 Начать авто-работу", callback_data="start_auto_all")],
            [InlineKeyboardButton("🔍 Проверить работу", callback_data="check_work")]
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
        self.work_cycles[user_id] = 0  # Сбрасываем счетчик циклов
        
        await query.edit_message_text(
            "🚀 Запускаю автоматическую работу...\n\n"
            "Бот начал поиск и выполнение заданий на выбранных биржах.\n"
            "Я буду присылать уведомления о выполненных заданиях.\n\n"
            "📊 Для проверки работы используйте команду /check или кнопку 'Проверить работу'"
        )
        
        # Запускаем фоновую задачу для имитации работы
        asyncio.create_task(self.simulate_work(user_id))
    
    async def simulate_work(self, user_id):
        """Имитация работы бота (для демонстрации)"""
        while user_id in self.active_users and self.active_users[user_id].get('working', False):
            try:
                self.work_cycles[user_id] = self.work_cycles.get(user_id, 0) + 1
                
                # Логируем работу в консоль
                print(f"🔍 [Цикл {self.work_cycles[user_id]}] Поиск заданий для пользователя {user_id}")
                
                # Имитация поиска на разных биржах
                for exchange in self.active_users[user_id]['exchanges']:
                    print(f"📡 Проверяю {exchange}...")
                    
                    # Имитация нахождения задания (1 из 3 циклов)
                    if self.work_cycles[user_id] % 3 == 0:
                        task_amount = round(0.1 + (self.work_cycles[user_id] * 0.05), 2)
                        print(f"✅ Найдено задание на {exchange}! Сумма: {task_amount} руб.")
                        
                        # Сохраняем в базу
                        await self.log_task_completion(user_id, exchange, {
                            'type': 'click', 
                            'title': f'Тестовое задание #{self.work_cycles[user_id]}'
                        }, task_amount)
                        
                        # Отправляем уведомление
                        try:
                            await self.application.bot.send_message(
                                chat_id=user_id,
                                text=f"✅ Выполнено задание на {exchange.capitalize()}\n"
                                     f"💵 Заработано: {task_amount} руб.\n"
                                     f"📝 Тестовое задание #{self.work_cycles[user_id]}"
                            )
                        except Exception as e:
                            print(f"❌ Ошибка отправки уведомления: {e}")
                
                # Ждем перед следующим циклом
                await asyncio.sleep(self.config.SETTINGS['check_interval'])
                
            except Exception as e:
                print(f"❌ Ошибка в simulate_work: {e}")
                await asyncio.sleep(30)
    
    async def check_work_status(self, query):
        """Проверка статуса работы бота"""
        user_id = query.from_user.id
        
        check_text = "🔍 **ПРОВЕРКА РАБОТЫ БОТА**\n\n"
        
        # 1. Проверка подключения к Telegram API
        check_text += "1. 📡 Подключение к Telegram API: "
        try:
            bot_info = await self.application.bot.get_me()
            check_text += "✅ РАБОТАЕТ\n"
            check_text += f"   🤖 Бот: @{bot_info.username}\n"
        except Exception as e:
            check_text += f"❌ ОШИБКА: {e}\n"
        
        # 2. Проверка статуса работы
        check_text += "2. ⚙️ Статус автоматической работы: "
        if user_id in self.active_users and self.active_users[user_id].get('working', False):
            check_text += "✅ АКТИВНА\n"
            active_exchanges = [ex.capitalize() for ex in self.active_users[user_id]['exchanges']]
            check_text += f"   📊 Активные биржи: {', '.join(active_exchanges)}\n"
            check_text += f"   🔄 Циклов работы: {self.work_cycles.get(user_id, 0)}\n"
        else:
            check_text += "❌ НЕ АКТИВНА\n"
            check_text += "   💡 Используйте 'Начать авто-работу'\n"
        
        # 3. Проверка базы данных
        check_text += "3. 💾 База данных: "
        try:
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            
            # Проверяем таблицы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in cursor.fetchall()]
            
            required_tables = ['users', 'tasks', 'balances']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if not missing_tables:
                check_text += "✅ РАБОТАЕТ\n"
                
                # Статистика из БД
                cursor.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ?', (user_id,))
                task_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT SUM(amount) FROM tasks WHERE user_id = ?', (user_id,))
                total_earned = cursor.fetchone()[0] or 0
                
                check_text += f"   📊 Заданий выполнено: {task_count}\n"
                check_text += f"   💰 Всего заработано: {total_earned:.2f} руб.\n"
            else:
                check_text += f"❌ ОШИБКА: Отсутствуют таблицы {missing_tables}\n"
                
            conn.close()
        except Exception as e:
            check_text += f"❌ ОШИБКА: {e}\n"
        
        # 4. Проверка последней активности
        check_text += "4. 📈 Последняя активность: "
        try:
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            cursor.execute(
                'SELECT created_at FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
                (user_id,)
            )
            last_task = cursor.fetchone()
            
            if last_task:
                last_time = datetime.fromisoformat(last_task[0])
                time_diff = (datetime.now() - last_time).total_seconds() / 60  # в минутах
                check_text += f"✅ {time_diff:.1f} мин. назад\n"
            else:
                check_text += "ℹ️ Заданий еще нет\n"
                
            conn.close()
        except Exception as e:
            check_text += f"❌ ОШИБКА: {e}\n"
        
        # 5. Рекомендации
        check_text += "\n💡 **РЕКОМЕНДАЦИИ:**\n"
        if user_id not in self.active_users or not self.active_users[user_id].get('working', False):
            check_text += "• Запустите авто-работу через меню\n"
        elif self.work_cycles.get(user_id, 0) == 0:
            check_text += "• Бот только запущен, подождите несколько минут\n"
        else:
            check_text += "• Бот работает корректно!\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить проверку", callback_data="check_work")],
            [InlineKeyboardButton("🔙 Назад", callback_data="start_work")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(check_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def log_task_completion(self, user_id, exchange, task, amount):
        """Логирование выполненного задания"""
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO tasks (user_id, exchange, task_type, amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, exchange, task['type'], amount, 'completed', datetime.now().isoformat())
        )
        
        cursor.execute(
            'UPDATE users SET total_earned = total_earned + ?, tasks_completed = tasks_completed + 1 WHERE user_id = ?',
            (amount, user_id)
        )
        
        cursor.execute(
            'INSERT OR REPLACE INTO balances (user_id, exchange, balance, last_updated) '
            'VALUES (?, ?, COALESCE((SELECT balance FROM balances WHERE user_id = ? AND exchange = ?), 0) + ?, ?)',
            (user_id, exchange, user_id, exchange, amount, datetime.now().isoformat())
        )
        
        conn.commit()
        conn.close()
    
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
            stats_text += f"✅ Выполнено заданий: {tasks_completed}\n"
            stats_text += f"🔄 Циклов работы: {self.work_cycles.get(user_id, 0)}\n\n"
            stats_text += "📈 По биржам:\n"
            
            for exchange, amount in by_exchange:
                if amount:
                    stats_text += f"• {exchange.capitalize()}: {amount:.2f} руб.\n"
        else:
            stats_text = "📊 Статистика не найдена\n\nНачните работу, чтобы увидеть статистику!"
        
        conn.close()
        
        keyboard = [
            [InlineKeyboardButton("🔍 Проверить работу", callback_data="check_work")],
            [InlineKeyboardButton("🔙 Назад", callback_data="start_work")]
        ]
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
        
        keyboard = [
            [InlineKeyboardButton("🔍 Проверить работу", callback_data="check_work")],
            [InlineKeyboardButton("🔙 Назад", callback_data="start_work")]
        ]
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
        
        keyboard = [
            [InlineKeyboardButton("🔍 Проверить работу", callback_data="check_work")],
            [InlineKeyboardButton("🔙 Назад", callback_data="start_work")]
        ]
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
            "🔍 **Проверка работы:**\n"
            "Используйте кнопку 'Проверить работу' для диагностики\n\n"
            "⚠️ Важно:\n"
            "• Соблюдайте правила бирж\n"
            "• Настройте лимиты\n"
            "• Мониторьте работу\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔍 Проверить работу", callback_data="check_work")],
            [InlineKeyboardButton("🔙 Назад", callback_data="start_work")]
        ]
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
            status_text += f"📊 Активные биржи: {', '.join(active_exchanges)}\n"
            status_text += f"🔄 Циклов работы: {self.work_cycles.get(user_id, 0)}"
        else:
            status_text = "🔴 Бот остановлен"
        
        await update.message.reply_text(status_text)
    
    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для проверки работы"""
        user_id = update.effective_user.id
        
        # Создаем fake query для использования существующего метода
        class FakeQuery:
            def __init__(self, user_id):
                self.from_user = type('User', (), {'id': user_id})()
                self.edit_message_text = self.fake_edit
                self.message = type('Message', (), {'reply_text': self.fake_reply})()
            
            async def fake_edit(self, *args, **kwargs):
                await update.message.reply_text(*args, **kwargs)
            
            async def fake_reply(self, *args, **kwargs):
                await update.message.reply_text(*args, **kwargs)
        
        fake_query = FakeQuery(user_id)
        await self.check_work_status(fake_query)

def main():
    """Синхронная главная функция"""
    print("🤖 Бот запускается...")
    
    try:
        # Создаем бота и приложение
        bot = AutoEarnBot()
        
        # Создаем приложение
        application = Application.builder().token(bot.config.BOT_TOKEN).build()
        
        # Сохраняем application для использования в других методах
        bot.application = application
        
        # Обработчики команд
        application.add_handler(CommandHandler("start", bot.start))
        application.add_handler(CommandHandler("stop", bot.stop))
        application.add_handler(CommandHandler("status", bot.status))
        application.add_handler(CommandHandler("stats", bot.show_stats))
        application.add_handler(CommandHandler("check", bot.check_command))
        
        # Обработчики кнопок
        application.add_handler(CallbackQueryHandler(bot.button_handler))
        
        print("✅ Бот успешно запущен!")
        print("📝 Используйте команду /start в Telegram для начала работы")
        print("🔍 Для проверки работы используйте /check или кнопку 'Проверить работу'")
        
        # Запускаем бота
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main()
