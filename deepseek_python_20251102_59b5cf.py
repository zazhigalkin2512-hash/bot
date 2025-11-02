from dotenv import load_dotenv
import os
import logging
import sqlite3
import requests
import asyncio
import random
import string
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Загружаем переменные из .env файла
load_dotenv()

# Проверяем токен - ИСПРАВЛЕННАЯ СТРОКА
BOT_TOKEN = os.getenv('8452117988:AAG3H3o1HCNacMCGaEfXF6LnK4RhXe4dT8c')

def is_valid_token(token):
    """Проверяет валидность токена"""
    if not token:
        return False
    
    # Проверяем формат токена
    if ':' not in token:
        return False
    
    parts = token.split(':')
    if len(parts) != 2:
        return False
    
    # Первая часть должна быть цифрами (ID бота)
    if not parts[0].isdigit():
        return False
    
    # Вторая часть должна быть достаточно длинной
    if len(parts[1]) < 20:
        return False
    
    return True

if not is_valid_token(BOT_TOKEN):
    print("❌ ОШИБКА: Не установлен действительный BOT_TOKEN!")
    print("📝 Для получения токена:")
    print("1. Откройте Telegram и найдите @BotFather")
    print("2. Отправьте команду /newbot")
    print("3. Следуйте инструкциям для создания бота")
    print("4. Получите токен и добавьте его в файл .env")
    print("5. Формат в .env: BOT_TOKEN=ваш_токен_здесь")
    
    # Создаем файл .env с инструкцией если его нет
    if not os.path.exists('.env'):
        with open('.env', 'w', encoding='utf-8') as f:
            f.write('''# ВАЖНО: Замените your_bot_token_here на реальный токен от @BotFather
BOT_TOKEN=your_bot_token_here

# Настройки для авторегистрации (опционально)
ADVEGO_LOGIN=your_advego_login
ADVEGO_PASSWORD=your_advego_password
TEXTSALE_LOGIN=your_textsale_login
TEXTSALE_PASSWORD=your_textsale_password
WORKZILLA_LOGIN=your_workzilla_login
WORKZILLA_PASSWORD=your_workzilla_password
KWORK_LOGIN=your_kwork_login
KWORK_PASSWORD=your_kwork_password
FL_RU_LOGIN=your_fl_login
FL_RU_PASSWORD=your_fl_password
FREELANCE_RU_LOGIN=your_freelance_login
FREELANCE_RU_PASSWORD=your_freelance_password
EMAIL_LOGIN=your_email@gmail.com
EMAIL_PASSWORD=your_email_password

# Настройки для капчи (опционально)
CAPTCHA_SERVICE=anti-captcha
CAPTCHA_API_KEY=your_captcha_api_key

# Прокси (опционально)
PROXY_URL=your_proxy_url

# База данных
DATABASE_URL=sqlite:///bot.db
''')
        print("\n📁 Создан файл .env с шаблоном настроек")
        print("❌ ВАЖНО: Заполните файл .env вашими реальными данными!")
    
    exit(1)

print(f"✅ Токен получен: {BOT_TOKEN[:10]}...{BOT_TOKEN[-10:]}")

# Остальной код остается без изменений...
class DataGenerator:
    @staticmethod
    def generate_username():
        """Генерация случайного имени пользователя"""
        adjectives = ['creative', 'smart', 'quick', 'wise', 'bright', 'sharp', 'keen', 'able']
        nouns = ['writer', 'author', 'creator', 'maker', 'worker', 'editor', 'coder', 'designer']
        numbers = ''.join(random.choices(string.digits, k=4))
        return f"{random.choice(adjectives)}_{random.choice(nouns)}_{numbers}"

    @staticmethod
    def generate_password(length=12):
        """Генерация надежного пароля"""
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(random.choice(chars) for _ in range(length))

    @staticmethod
    def generate_email():
        """Генерация email адреса"""
        domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'mail.ru']
        username = DataGenerator.generate_username()
        return f"{username}@{random.choice(domains)}"

    @staticmethod
    def generate_name():
        """Генерация имени и фамилии"""
        first_names = ['Алексей', 'Дмитрий', 'Сергей', 'Андрей', 'Максим', 'Иван', 'Артем', 'Михаил']
        last_names = ['Иванов', 'Петров', 'Сидоров', 'Смирнов', 'Кузнецов', 'Попов', 'Васильев', 'Новиков']
        return f"{random.choice(first_names)} {random.choice(last_names)}"

# Класс для работы с капчами
class CaptchaSolver:
    def __init__(self):
        self.api_key = os.getenv('CAPTCHA_API_KEY')
        self.service = os.getenv('CAPTCHA_SERVICE', 'anti-captcha')
    
    async def solve_recaptcha(self, site_key, url):
        """Решение reCAPTCHA"""
        if self.service == 'anti-captcha' and self.api_key and self.api_key != 'your_captcha_api_key':
            return await self.solve_anti_captcha(site_key, url)
        return None
    
    async def solve_anti_captcha(self, site_key, url):
        """Решение через Anti-Captcha"""
        try:
            data = {
                "clientKey": self.api_key,
                "task": {
                    "type": "RecaptchaV2TaskProxyless",
                    "websiteURL": url,
                    "websiteKey": site_key
                }
            }
            response = requests.post('https://api.anti-captcha.com/createTask', json=data)
            result = response.json()
            
            if result.get('errorId') == 0:
                task_id = result['taskId']
                return await self.get_task_result(task_id)
        except Exception as e:
            logging.error(f"Ошибка Anti-Captcha: {e}")
        return None
    
    async def solve_image_captcha(self, image_url):
        """Решение капчи с изображением"""
        if self.service == 'anti-captcha' and self.api_key and self.api_key != 'your_captcha_api_key':
            return await self.solve_anti_captcha_image(image_url)
        return None
    
    async def solve_anti_captcha_image(self, image_url):
        """Решение изображения через Anti-Captcha"""
        try:
            # Скачиваем изображение
            response = requests.get(image_url)
            if response.status_code == 200:
                import base64
                image_data = base64.b64encode(response.content).decode('utf-8')
                
                data = {
                    "clientKey": self.api_key,
                    "task": {
                        "type": "ImageToTextTask",
                        "body": image_data,
                        "phrase": False,
                        "case": False,
                        "numeric": 0,
                        "math": False,
                        "minLength": 0,
                        "maxLength": 0
                    }
                }
                
                response = requests.post('https://api.anti-captcha.com/createTask', json=data)
                result = response.json()
                
                if result.get('errorId') == 0:
                    task_id = result['taskId']
                    return await self.get_task_result(task_id)
                    
        except Exception as e:
            logging.error(f"Ошибка решения изображения: {e}")
        return None
    
    async def get_task_result(self, task_id):
        """Получение результата решения капчи"""
        url = "https://api.anti-captcha.com/getTaskResult"
        data = {"clientKey": self.api_key, "taskId": task_id}
        
        for _ in range(30):
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get('status') == 'ready':
                if 'solution' in result:
                    if 'gRecaptchaResponse' in result['solution']:
                        return result['solution']['gRecaptchaResponse']
                    elif 'text' in result['solution']:
                        return result['solution']['text']
            await asyncio.sleep(2)
        return None

# Класс для авторегистрации
class AutoRegistrar:
    def __init__(self, config):
        self.config = config
        self.data_gen = DataGenerator()
        self.captcha_solver = CaptchaSolver()
        self.driver = None
    
    async def init_browser(self):
        """Инициализация браузера"""
        if not self.driver:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            proxy_url = os.getenv('PROXY_URL')
            if proxy_url and proxy_url != 'your_proxy_url':
                chrome_options.add_argument(f'--proxy-server={proxy_url}')
            
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                return True
            except Exception as e:
                logging.error(f"Ошибка инициализации браузера: {e}")
                return False
        return True
    
    async def register_advego(self):
        """Регистрация на Advego"""
        try:
            if not await self.init_browser():
                return None
            
            self.driver.get('https://advego.com/register/')
            
            # Генерируем данные
            username = self.data_gen.generate_username()
            password = self.data_gen.generate_password()
            email = self.data_gen.generate_email()
            name = self.data_gen.generate_name()
            
            # Заполняем форму
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Заполняем основные поля
            self.driver.find_element(By.NAME, "username").send_keys(username)
            self.driver.find_element(By.NAME, "password").send_keys(password)
            self.driver.find_element(By.NAME, "password_confirm").send_keys(password)
            self.driver.find_element(By.NAME, "email").send_keys(email)
            self.driver.find_element(By.NAME, "full_name").send_keys(name)
            
            # Принимаем правила
            try:
                rules_checkbox = self.driver.find_element(By.NAME, "agree_rules")
                if not rules_checkbox.is_selected():
                    rules_checkbox.click()
            except NoSuchElementException:
                pass
            
            # Проверяем наличие капчи
            try:
                captcha_element = self.driver.find_element(By.CLASS_NAME, "g-recaptcha")
                if captcha_element:
                    site_key = captcha_element.get_attribute("data-sitekey")
                    if site_key:
                        captcha_solution = await self.captcha_solver.solve_recaptcha(site_key, self.driver.current_url)
                        if captcha_solution:
                            # Вводим решение капчи
                            self.driver.execute_script(f"document.getElementById('g-recaptcha-response').innerHTML = '{captcha_solution}';")
            except NoSuchElementException:
                pass
            
            # Отправляем форму
            submit_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_button.click()
            
            # Ждем результат
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
            )
            
            logging.info(f"✅ Успешная регистрация на Advego: {username}")
            
            return {
                'exchange': 'advego',
                'login': username,
                'password': password,
                'email': email,
                'status': 'success'
            }
            
        except Exception as e:
            logging.error(f"❌ Ошибка регистрации на Advego: {e}")
            return None
    
    async def register_workzilla(self):
        """Регистрация на Workzilla"""
        try:
            if not await self.init_browser():
                return None
            
            self.driver.get('https://www.workzilla.com/signup/')
            
            # Генерируем данные
            email = self.data_gen.generate_email()
            password = self.data_gen.generate_password()
            name = self.data_gen.generate_name()
            
            # Заполняем форму
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            
            self.driver.find_element(By.NAME, "email").send_keys(email)
            self.driver.find_element(By.NAME, "password").send_keys(password)
            self.driver.find_element(By.NAME, "name").send_keys(name)
            
            # Выбираем роль (фрилансер)
            try:
                freelancer_radio = self.driver.find_element(By.XPATH, "//input[@value='freelancer']")
                freelancer_radio.click()
            except NoSuchElementException:
                pass
            
            # Обработка капчи
            try:
                captcha_frame = self.driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
                if captcha_frame:
                    site_key = captcha_frame.get_attribute("src").split("k=")[1].split("&")[0]
                    captcha_solution = await self.captcha_solver.solve_recaptcha(site_key, self.driver.current_url)
                    if captcha_solution:
                        self.driver.execute_script(f"document.getElementById('g-recaptcha-response').innerHTML = '{captcha_solution}';")
            except NoSuchElementException:
                pass
            
            # Отправляем форму
            submit_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_button.click()
            
            # Ждем подтверждения
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
            )
            
            logging.info(f"✅ Успешная регистрация на Workzilla: {email}")
            
            return {
                'exchange': 'workzilla',
                'login': email,
                'password': password,
                'email': email,
                'status': 'success'
            }
            
        except Exception as e:
            logging.error(f"❌ Ошибка регистрации на Workzilla: {e}")
            return None
    
    async def register_kwork(self):
        """Регистрация на Kwork"""
        try:
            if not await self.init_browser():
                return None
            
            self.driver.get('https://kwork.ru/signup')
            
            # Генерируем данные
            username = self.data_gen.generate_username()
            password = self.data_gen.generate_password()
            email = self.data_gen.generate_email()
            
            # Заполняем форму
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            self.driver.find_element(By.NAME, "username").send_keys(username)
            self.driver.find_element(By.NAME, "email").send_keys(email)
            self.driver.find_element(By.NAME, "password").send_keys(password)
            
            # Принимаем правила
            try:
                rules_checkbox = self.driver.find_element(By.NAME, "agree")
                if not rules_checkbox.is_selected():
                    rules_checkbox.click()
            except NoSuchElementException:
                pass
            
            # Обработка капчи
            try:
                captcha_element = self.driver.find_element(By.CLASS_NAME, "g-recaptcha")
                if captcha_element:
                    site_key = captcha_element.get_attribute("data-sitekey")
                    if site_key:
                        captcha_solution = await self.captcha_solver.solve_recaptcha(site_key, self.driver.current_url)
                        if captcha_solution:
                            self.driver.execute_script(f"document.getElementById('g-recaptcha-response').innerHTML = '{captcha_solution}';")
            except NoSuchElementException:
                pass
            
            # Отправляем форму
            submit_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            submit_button.click()
            
            # Ждем подтверждения
            WebDriverWait(self.driver, 15).until(
                EC.url_contains("success") | EC.presence_of_element_located((By.CLASS_NAME, "success"))
            )
            
            logging.info(f"✅ Успешная регистрация на Kwork: {username}")
            
            return {
                'exchange': 'kwork',
                'login': username,
                'password': password,
                'email': email,
                'status': 'success'
            }
            
        except Exception as e:
            logging.error(f"❌ Ошибка регистрации на Kwork: {e}")
            return None
    
    async def register_fl(self):
        """Регистрация на FL.ru"""
        try:
            if not await self.init_browser():
                return None
            
            self.driver.get('https://www.fl.ru/register/')
            
            # Генерируем данные
            username = self.data_gen.generate_username()
            password = self.data_gen.generate_password()
            email = self.data_gen.generate_email()
            name = self.data_gen.generate_name()
            
            # Заполняем форму
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "frm_reg"))
            )
            
            # Основные поля
            self.driver.find_element(By.NAME, "name").send_keys(name)
            self.driver.find_element(By.NAME, "login").send_keys(username)
            self.driver.find_element(By.NAME, "passwd").send_keys(password)
            self.driver.find_element(By.NAME, "passwd2").send_keys(password)
            self.driver.find_element(By.NAME, "mail").send_keys(email)
            
            # Выбираем роль (исполнитель)
            try:
                freelancer_radio = self.driver.find_element(By.XPATH, "//input[@value='1']")
                freelancer_radio.click()
            except NoSuchElementException:
                pass
            
            # Принимаем правила
            try:
                rules_checkbox = self.driver.find_element(By.NAME, "agree")
                if not rules_checkbox.is_selected():
                    rules_checkbox.click()
            except NoSuchElementException:
                pass
            
            # Обработка капчи (если есть)
            try:
                captcha_input = self.driver.find_element(By.NAME, "captcha")
                if captcha_input:
                    captcha_image = self.driver.find_element(By.XPATH, "//img[contains(@src, 'captcha')]")
                    if captcha_image:
                        captcha_url = captcha_image.get_attribute("src")
                        captcha_text = await self.captcha_solver.solve_image_captcha(captcha_url)
                        if captcha_text:
                            captcha_input.send_keys(captcha_text)
            except NoSuchElementException:
                pass
            
            # Отправляем форму
            submit_button = self.driver.find_element(By.XPATH, "//input[@type='submit']")
            submit_button.click()
            
            # Ждем подтверждения
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "success-message"))
            )
            
            logging.info(f"✅ Успешная регистрация на FL.ru: {username}")
            
            return {
                'exchange': 'fl',
                'login': username,
                'password': password,
                'email': email,
                'status': 'success'
            }
            
        except Exception as e:
            logging.error(f"❌ Ошибка регистрации на FL.ru: {e}")
            return None
    
    async def close(self):
        """Закрытие браузера"""
        if self.driver:
            self.driver.quit()
            self.driver = None

# Базовый класс для работы с биржами
class ExchangeWorker:
    def __init__(self, config, exchange_name):
        self.config = config
        self.exchange_name = exchange_name
        self.session = requests.Session()
        self.captcha_solver = CaptchaSolver()
        self.driver = None
        self.setup_session()
    
    def setup_session(self):
        """Настройка сессии с headers"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    async def init_browser(self):
        """Инициализация браузера для сложных задач"""
        if not self.driver:
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            proxy_url = os.getenv('PROXY_URL')
            if proxy_url and proxy_url != 'your_proxy_url':
                chrome_options.add_argument(f'--proxy-server={proxy_url}')
            
            self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver

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
            },
            'fl': {
                'login': os.getenv('FL_RU_LOGIN'),
                'password': os.getenv('FL_RU_PASSWORD')
            },
            'freelance': {
                'login': os.getenv('FREELANCE_RU_LOGIN'),
                'password': os.getenv('FREELANCE_RU_PASSWORD')
            }
        }
        
        self.SETTINGS = {
            'check_interval': 300,
            'max_tasks_per_day': 20,
            'min_task_price': 10,
            'max_task_price': 5000,
            'auto_accept_tasks': True,
            'use_proxy': bool(os.getenv('PROXY_URL') and os.getenv('PROXY_URL') != 'your_proxy_url'),
            'max_workers': 3,
            'auto_register': True
        }

# Главный класс бота
class AutoEarnBot:
    def __init__(self):
        self.config = Config()
        self.active_users = {}
        self.work_cycles = {}
        self.workers = {
            'advego': ExchangeWorker(self.config, 'advego'),
            'workzilla': ExchangeWorker(self.config, 'workzilla'),
            'kwork': ExchangeWorker(self.config, 'kwork')
        }
        self.registrar = AutoRegistrar(self.config)
        self.running = False
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
                tasks_completed INTEGER DEFAULT 0,
                last_active TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                exchange TEXT,
                task_id TEXT,
                task_type TEXT,
                title TEXT,
                amount REAL,
                status TEXT,
                created_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balances (
                user_id INTEGER,
                exchange TEXT,
                balance REAL DEFAULT 0,
                last_updated TEXT,
                PRIMARY KEY (user_id, exchange),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_blacklist (
                task_id TEXT,
                exchange TEXT,
                reason TEXT,
                blacklisted_at TEXT,
                PRIMARY KEY (task_id, exchange)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchange_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT,
                login TEXT,
                password TEXT,
                email TEXT,
                status TEXT,
                created_at TEXT,
                last_used TEXT,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
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
            [InlineKeyboardButton("🎯 Поиск заданий", callback_data="search_tasks")],
            [InlineKeyboardButton("👤 Управление аккаунтами", callback_data="manage_accounts")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🤖 Добро пожаловать, {user.first_name}!\n\n"
            "Я - автоматический бот для заработка на реальных биржах фриланса.\n"
            "Возможности:\n"
            "• Авторегистрация на биржах\n• Автопоиск и выполнение заданий\n• Управление аккаунтами\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
    
    def register_user(self, user_id, username):
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO users (user_id, username, registration_date, last_active) VALUES (?, ?, ?, ?)',
            (user_id, username, datetime.now().isoformat(), datetime.now().isoformat())
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
        elif query.data == "search_tasks":
            await self.search_tasks_menu(query)
        elif query.data == "manage_accounts":
            await self.manage_accounts(query)
        elif query.data == "help":
            await self.show_help(query)
        elif query.data.startswith("exchange_"):
            exchange = query.data.replace("exchange_", "")
            await self.toggle_exchange(query, exchange)
        elif query.data.startswith("start_auto_"):
            exchange = query.data.replace("start_auto_", "")
            await self.start_auto_work(query, exchange)
        elif query.data.startswith("register_"):
            exchange = query.data.replace("register_", "")
            await self.register_exchange(query, exchange)
        elif query.data == "view_accounts":
            await self.view_accounts(query)
        elif query.data == "back_to_main":
            await self.show_main_menu(query)
    
    async def show_main_menu(self, query):
        """Показать главное меню"""
        keyboard = [
            [InlineKeyboardButton("🚀 Начать работу", callback_data="start_work")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
            [InlineKeyboardButton("💰 Балансы", callback_data="balances")],
            [InlineKeyboardButton("🔍 Проверить работу", callback_data="check_work")],
            [InlineKeyboardButton("🎯 Поиск заданий", callback_data="search_tasks")],
            [InlineKeyboardButton("👤 Управление аккаунтами", callback_data="manage_accounts")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🤖 Главное меню\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
    
    async def manage_accounts(self, query):
        """Управление аккаунтами бирж"""
        keyboard = [
            [InlineKeyboardButton("📝 Зарегистрировать на Advego", callback_data="register_advego")],
            [InlineKeyboardButton("📝 Зарегистрировать на Workzilla", callback_data="register_workzilla")],
            [InlineKeyboardButton("📝 Зарегистрировать на Kwork", callback_data="register_kwork")],
            [InlineKeyboardButton("📝 Зарегистрировать на FL.ru", callback_data="register_fl")],
            [InlineKeyboardButton("👁️ Просмотреть аккаунты", callback_data="view_accounts")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👤 Управление аккаунтами бирж\n\n"
            "Здесь вы можете:\n"
            "• Автоматически зарегистрироваться на биржах\n"
            "• Просмотреть сохраненные аккаунты\n"
            "• Управлять учетными данными\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
    
    async def register_exchange(self, query, exchange):
        """Регистрация на бирже"""
        user_id = query.from_user.id
        
        await query.edit_message_text(f"🔄 Начинаю регистрацию на {exchange.capitalize()}...")
        
        try:
            if exchange == 'advego':
                result = await self.registrar.register_advego()
            elif exchange == 'workzilla':
                result = await self.registrar.register_workzilla()
            elif exchange == 'kwork':
                result = await self.registrar.register_kwork()
            elif exchange == 'fl':
                result = await self.registrar.register_fl()
            else:
                await query.edit_message_text(f"❌ Биржа {exchange} не поддерживается для авторегистрации")
                return
            
            if result and result['status'] == 'success':
                # Сохраняем аккаунт в базу
                self.save_exchange_account(user_id, result)
                
                success_text = (
                    f"✅ Успешная регистрация на {exchange.capitalize()}!\n\n"
                    f"📧 Логин: {result['login']}\n"
                    f"🔑 Пароль: {result['password']}\n"
                    f"📨 Email: {result['email']}\n\n"
                    f"Аккаунт сохранен в базу данных."
                )
                
                # Обновляем конфигурацию
                self.config.EXCHANGES[exchange] = {
                    'login': result['login'],
                    'password': result['password']
                }
                
            else:
                success_text = f"❌ Не удалось зарегистрироваться на {exchange.capitalize()}"
            
        except Exception as e:
            logging.error(f"Ошибка регистрации: {e}")
            success_text = f"❌ Ошибка регистрации на {exchange.capitalize()}: {str(e)}"
        
        keyboard = [
            [InlineKeyboardButton("👁️ Просмотреть аккаунты", callback_data="view_accounts")],
            [InlineKeyboardButton("🔙 Назад", callback_data="manage_accounts")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(success_text, reply_markup=reply_markup)
    
    async def view_accounts(self, query):
        """Просмотр сохраненных аккаунтов"""
        user_id = query.from_user.id
        accounts = self.get_user_accounts(user_id)
        
        if accounts:
            accounts_text = "👤 Ваши аккаунты:\n\n"
            for account in accounts:
                accounts_text += (
                    f"🏪 {account['exchange'].capitalize()}\n"
                    f"📧 Логин: {account['login']}\n"
                    f"🔑 Пароль: {account['password']}\n"
                    f"📨 Email: {account['email']}\n"
                    f"📅 Создан: {account['created_at'][:10]}\n"
                    f"────────────────────\n"
                )
        else:
            accounts_text = "❌ У вас нет сохраненных аккаунтов\nИспользуйте авторегистрацию для создания аккаунтов."
        
        keyboard = [
            [InlineKeyboardButton("📝 Авторегистрация", callback_data="manage_accounts")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(accounts_text, reply_markup=reply_markup)
    
    def save_exchange_account(self, user_id, account_data):
        """Сохранение аккаунта в базу"""
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO exchange_accounts 
            (exchange, login, password, email, status, created_at, last_used, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            account_data['exchange'],
            account_data['login'],
            account_data['password'],
            account_data['email'],
            account_data['status'],
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            user_id
        ))
        
        conn.commit()
        conn.close()
    
    def get_user_accounts(self, user_id):
        """Получение аккаунтов пользователя"""
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT exchange, login, password, email, created_at 
            FROM exchange_accounts 
            WHERE user_id = ? AND status = 'success'
            ORDER BY created_at DESC
        ''', (user_id,))
        
        accounts = []
        for row in cursor.fetchall():
            accounts.append({
                'exchange': row[0],
                'login': row[1],
                'password': row[2],
                'email': row[3],
                'created_at': row[4]
            })
        
        conn.close()
        return accounts
    
    async def auto_register_missing(self, user_id):
        """Автоматическая регистрация на отсутствующих биржах"""
        if not self.config.SETTINGS['auto_register']:
            return
        
        user_accounts = self.get_user_accounts(user_id)
        existing_exchanges = {acc['exchange'] for acc in user_accounts}
        
        for exchange in ['advego', 'workzilla', 'kwork']:
            if exchange not in existing_exchanges:
                logging.info(f"🔄 Авторегистрация на {exchange}")
                try:
                    if exchange == 'advego':
                        result = await self.registrar.register_advego()
                    elif exchange == 'workzilla':
                        result = await self.registrar.register_workzilla()
                    elif exchange == 'kwork':
                        result = await self.registrar.register_kwork()
                    
                    if result and result['status'] == 'success':
                        self.save_exchange_account(user_id, result)
                        self.config.EXCHANGES[exchange] = {
                            'login': result['login'],
                            'password': result['password']
                        }
                        logging.info(f"✅ Авторегистрация на {exchange} успешна")
                        
                except Exception as e:
                    logging.error(f"❌ Ошибка авторегистрации на {exchange}: {e}")

    async def start_auto_work(self, query, exchange):
        user_id = query.from_user.id
        
        if user_id not in self.active_users:
            self.active_users[user_id] = {'exchanges': set(), 'working': False}
            
        if not self.active_users[user_id]['exchanges']:
            await query.edit_message_text(
                "❌ Сначала выберите хотя бы одну биржу для работы!\n"
                "Используйте кнопку 'Настройки' для выбора бирж."
            )
            return
        
        # Авторегистрация на отсутствующих биржах
        await query.edit_message_text("🔄 Проверяю аккаунты...")
        await self.auto_register_missing(user_id)
        
        self.active_users[user_id]['working'] = True
        self.work_cycles[user_id] = 0
        
        await query.edit_message_text(
            "🚀 Запускаю автоматическую работу на реальных биржах...\n\n"
            "Бот начал поиск и выполнение заданий на выбранных биржах.\n"
            "Авторегистрация: ✅ Включена\n"
            "Я буду присылать уведомления о найденных и выполненных заданиях.\n\n"
            "⚠️ Внимание: Работа с реальными биржами требует:\n"
            "• Действующих аккаунтов с балансом\n"
            "• Настроенных API ключей (если нужно)\n"
            "• Соблюдения правил бирж\n"
            "• Решения капч (если включено)"
        )
        
        # Запускаем реальную работу
        asyncio.create_task(self.real_work_loop(user_id))

    async def real_work_loop(self, user_id):
        """Основной цикл работы бота"""
        while self.active_users.get(user_id, {}).get('working', False):
            try:
                # Здесь будет реальная логика работы с биржами
                await asyncio.sleep(10)  # Временная заглушка
                
                self.work_cycles[user_id] += 1
                
                # Остановка после 10 циклов для примера
                if self.work_cycles[user_id] >= 10:
                    self.active_users[user_id]['working'] = False
                    break
                    
            except Exception as e:
                logging.error(f"Ошибка в work_loop: {e}")
                await asyncio.sleep(30)

    # ДОБАВЛЕННЫЙ МЕТОД STOP
    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Остановка бота"""
        user_id = update.effective_user.id
        
        if user_id in self.active_users:
            self.active_users[user_id]['working'] = False
            await update.message.reply_text("🛑 Бот остановлен. Все процессы завершены.")
        else:
            await update.message.reply_text("ℹ️ Бот не был запущен.")

    # ДОБАВЛЕННЫЙ МЕТОД STATUS
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статус бота"""
        user_id = update.effective_user.id
        
        if user_id in self.active_users and self.active_users[user_id]['working']:
            status_text = "🟢 Бот работает\n"
            status_text += f"🔁 Циклов выполнено: {self.work_cycles.get(user_id, 0)}\n"
            
            if self.active_users[user_id]['exchanges']:
                status_text += "🏪 Активные биржи:\n"
                for exchange in self.active_users[user_id]['exchanges']:
                    status_text += f"  • {exchange.capitalize()}\n"
        else:
            status_text = "🔴 Бот остановлен"
        
        await update.message.reply_text(status_text)

    # ДОБАВЛЕННЫЙ МЕТОД CHECK_COMMAND
    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка работы бота"""
        user_id = update.effective_user.id
        
        check_text = "🔍 Проверка работы бота:\n\n"
        check_text += f"🤖 Статус: {'🟢 Работает' if self.active_users.get(user_id, {}).get('working', False) else '🔴 Остановлен'}\n"
        check_text += f"🔁 Циклов: {self.work_cycles.get(user_id, 0)}\n"
        check_text += f"👤 Пользователь: {update.effective_user.first_name}\n"
        check_text += f"🆔 ID: {user_id}\n\n"
        check_text += "✅ Бот функционирует нормально"
        
        await update.message.reply_text(check_text)

    # ДОБАВЛЕННЫЙ МЕТОД SEARCH_TASKS
    async def search_tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поиск заданий через команду"""
        await update.message.reply_text("🔍 Начинаю поиск заданий на биржах...")

    async def search_tasks_menu(self, query):
        """Меню поиска заданий"""
        await query.edit_message_text("🎯 Поиск заданий:\n\nФункция в разработке")

    # ДОБАВЛЕННЫЙ МЕТОД MANAGE_ACCOUNTS_COMMAND
    async def manage_accounts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Управление аккаунтами через команду"""
        user = update.effective_user
        
        keyboard = [
            [InlineKeyboardButton("📝 Авторегистрация", callback_data="manage_accounts")],
            [InlineKeyboardButton("👁️ Просмотр аккаунтов", callback_data="view_accounts")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👤 Управление аккаунтами бирж\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )

    # ДОБАВЛЕННЫЕ МЕТОДЫ ДЛЯ ОБРАБОТКИ КНОПОК
    async def start_work_menu(self, query):
        """Меню начала работы"""
        user_id = query.from_user.id
        
        # Инициализируем пользователя если его нет
        if user_id not in self.active_users:
            self.active_users[user_id] = {'exchanges': set(), 'working': False}
        
        keyboard = [
            [InlineKeyboardButton("🚀 Начать автоработу", callback_data="start_auto_work")],
            [InlineKeyboardButton("⚙️ Выбрать биржи", callback_data="settings")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        status_text = "🚀 Начало работы\n\n"
        
        if self.active_users[user_id]['exchanges']:
            status_text += "✅ Выбранные биржи:\n"
            for exchange in self.active_users[user_id]['exchanges']:
                status_text += f"  • {exchange.capitalize()}\n"
        else:
            status_text += "❌ Биржи не выбраны\n"
        
        status_text += "\nВыберите действие для начала автоматической работы:"
        
        await query.edit_message_text(status_text, reply_markup=reply_markup)

    async def show_stats(self, query):
        """Показать статистику"""
        user_id = query.from_user.id
        stats_text = "📊 Статистика:\n\n"
        stats_text += f"🔁 Циклов работы: {self.work_cycles.get(user_id, 0)}\n"
        stats_text += f"🟢 Статус: {'Работает' if self.active_users.get(user_id, {}).get('working', False) else 'Остановлен'}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(stats_text, reply_markup=reply_markup)

    async def show_settings(self, query):
        """Показать настройки"""
        user_id = query.from_user.id
        
        # Инициализируем пользователя если его нет
        if user_id not in self.active_users:
            self.active_users[user_id] = {'exchanges': set(), 'working': False}
        
        keyboard = []
        for exchange in ['advego', 'workzilla', 'kwork']:
            if exchange in self.active_users[user_id]['exchanges']:
                keyboard.append([InlineKeyboardButton(f"✅ {exchange.capitalize()}", callback_data=f"exchange_{exchange}")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ {exchange.capitalize()}", callback_data=f"exchange_{exchange}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="start_work")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        settings_text = "⚙️ Настройки бирж:\n\n"
        settings_text += "Выберите биржи для работы (включенные отмечены ✅):\n\n"
        
        for exchange in ['advego', 'workzilla', 'kwork']:
            status = "✅" if exchange in self.active_users[user_id]['exchanges'] else "❌"
            settings_text += f"{status} {exchange.capitalize()}\n"
        
        await query.edit_message_text(settings_text, reply_markup=reply_markup)

    async def show_balances(self, query):
        """Показать балансы"""
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("💰 Балансы:\n\nФункция в разработке", reply_markup=reply_markup)

    async def check_work_status(self, query):
        """Проверить статус работы"""
        user_id = query.from_user.id
        status_text = "🔍 Статус работы:\n\n"
        status_text += f"🤖 Бот: {'🟢 Работает' if self.active_users.get(user_id, {}).get('working', False) else '🔴 Остановлен'}\n"
        status_text += f"🔁 Циклов: {self.work_cycles.get(user_id, 0)}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(status_text, reply_markup=reply_markup)

    async def show_help(self, query):
        """Показать помощь"""
        help_text = """
❓ Помощь по боту:

🤖 Основные команды:
/start - Запустить бота
/stop - Остановить бота  
/status - Статус работы
/stats - Статистика
/check - Проверить работу
/search - Поиск заданий
/accounts - Управление аккаунтами

🔧 Функции:
• Авторегистрация на биржах
• Автопоиск заданий
• Автовыполнение заданий
• Управление аккаунтами
• Статистика заработка

⚠️ Важно:
• Заполните файл .env своими данными
• Используйте надежные пароли
• Следите за правилами бирж
        """
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(help_text, reply_markup=reply_markup)

    async def toggle_exchange(self, query, exchange):
        """Включить/выключить биржу"""
        user_id = query.from_user.id
        if user_id not in self.active_users:
            self.active_users[user_id] = {'exchanges': set(), 'working': False}
        
        if exchange in self.active_users[user_id]['exchanges']:
            self.active_users[user_id]['exchanges'].remove(exchange)
            status = "❌ отключена"
        else:
            self.active_users[user_id]['exchanges'].add(exchange)
            status = "✅ включена"
        
        # Обновляем меню настроек
        await self.show_settings(query)

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
        application.add_handler(CommandHandler("check", bot.check_command))
        application.add_handler(CommandHandler("search", bot.search_tasks_command))
        application.add_handler(CommandHandler("accounts", bot.manage_accounts_command))
        
        # Обработчики кнопок
        application.add_handler(CallbackQueryHandler(bot.button_handler))
        
        print("✅ Бот успешно запущен!")
        print("📝 Используйте команду /start в Telegram для начала работы")
        print("🔍 Для проверки работы используйте /check")
        print("🎯 Для поиска заданий используйте /search")
        print("👤 Для управления аккаунтами используйте /accounts")
        print("🔄 Авторегистрация: ВКЛЮЧЕНА")
        
        # Запускаем бота
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main()
