import sqlite3
import random
import re
import os
DB_PATH = os.getenv('DATABASE_PATH', '/app/data/tarot_bot.db')
import hashlib
import hmac
import aiohttp
from datetime import datetime, timedelta


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance INTEGER DEFAULT 1,
        subscribed BOOLEAN DEFAULT 0,
        banned BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS saved_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        slot INTEGER,
        cards TEXT,
        interpretation TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, slot)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount_rub REAL,
        pack_size INTEGER,
        crypto_amount REAL,
        crypto_currency TEXT,
        payment_id TEXT UNIQUE,
        status TEXT DEFAULT 'waiting',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_data (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        birthdate TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_card (
        user_id INTEGER PRIMARY KEY,
        last_used DATE DEFAULT CURRENT_DATE,
        card_name TEXT,
        interpretation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reading_stats (
        user_id INTEGER PRIMARY KEY,
        total_readings INTEGER DEFAULT 0,
        last_reading TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, balance) VALUES (?, ?, ?, 1)', (user_id, username, first_name))
    cursor.execute('INSERT OR IGNORE INTO reading_stats (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 1

def decrease_balance(user_id, amount=1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?', (amount, user_id, amount))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def increase_balance(user_id, amount=1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def add_referral(referrer_id, referred_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM referrals WHERE referred_id = ?', (referred_id,))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute('INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)', (referrer_id, referred_id))
    cursor.execute('UPDATE users SET balance = balance + 1 WHERE user_id = ?', (referrer_id,))
    conn.commit()
    conn.close()
    return True

def mark_subscribed(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET subscribed = 1, balance = balance + 3 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True

def check_subscribed(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT subscribed FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_saved_slots(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT slot, timestamp FROM saved_readings WHERE user_id = ? ORDER BY slot ASC', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return {row[0]: row[1][:16] for row in results}

def save_reading(user_id, cards, interpretation, slot=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if slot is None:
        occupied = get_saved_slots(user_id).keys()
        for i in range(1, 4):
            if i not in occupied:
                slot = i
                break
    if slot is None or slot not in [1, 2, 3]:
        conn.close()
        return None
    cards_str = ','.join([card[0] for card in cards])
    cursor.execute('INSERT OR REPLACE INTO saved_readings (user_id, slot, cards, interpretation) VALUES (?, ?, ?, ?)', (user_id, slot, cards_str, interpretation))
    conn.commit()
    conn.close()
    return slot

def get_saved_reading(user_id, slot):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT cards, interpretation, timestamp FROM saved_readings WHERE user_id = ? AND slot = ?', (user_id, slot))
    result = cursor.fetchone()
    conn.close()
    return result

def delete_saved_reading(user_id, slot):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM saved_readings WHERE user_id = ? AND slot = ?', (user_id, slot))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def create_payment(user_id, amount_rub, pack_size, payment_id, crypto_currency, crypto_amount):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO payments (user_id, amount_rub, pack_size, payment_id, crypto_currency, crypto_amount)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, amount_rub, pack_size, payment_id, crypto_currency, crypto_amount))
    conn.commit()
    conn.close()

def complete_payment(payment_id, tx_hash):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, pack_size FROM payments WHERE payment_id = ? AND status = "waiting"', (payment_id,))
    result = cursor.fetchone()
    if result:
        user_id, pack_size = result
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (pack_size, user_id))
        cursor.execute('UPDATE payments SET status = "completed", completed_at = CURRENT_TIMESTAMP WHERE payment_id = ?', (payment_id,))
        conn.commit()
        conn.close()
        return user_id, pack_size
    else:
        conn.close()
        return None, None

def save_user_data(user_id, name, birthdate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO user_data (user_id, name, birthdate, updated_at)
    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, name, birthdate))
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT name, birthdate FROM user_data WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {'name': result[0], 'birthdate': result[1]}
    return None

def get_referral_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def can_get_daily_card(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT last_used FROM daily_card WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if not result:
        return True
    last_used = result[0]
    today = datetime.now().date().isoformat()
    return last_used != today

def save_daily_card(user_id, card_name, interpretation):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now().date().isoformat()
    cursor.execute('''
    INSERT OR REPLACE INTO daily_card (user_id, last_used, card_name, interpretation, created_at)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, today, card_name, interpretation))
    conn.commit()
    conn.close()

def get_daily_card(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now().date().isoformat()
    cursor.execute('SELECT card_name, interpretation FROM daily_card WHERE user_id = ? AND last_used = ?', (user_id, today))
    result = cursor.fetchone()
    conn.close()
    return result if result else None

def increment_reading_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR IGNORE INTO reading_stats (user_id, total_readings) VALUES (?, 0)
    ''', (user_id,))
    cursor.execute('''
    UPDATE reading_stats SET total_readings = total_readings + 1, last_reading = CURRENT_TIMESTAMP
    WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

def get_reading_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT total_readings FROM reading_stats WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_card_image_path(card_name):
    CARD_IMAGE_FILES = {
        "Шут": "00_fool.jpg", "Маг": "01_magician.jpg", "Жрица": "02_high_priestess.jpg",
        "Императрица": "03_empress.jpg", "Император": "04_emperor.jpg", "Жрец": "05_hierophant.jpg",
        "Влюблённые": "06_lovers.jpg", "Колесница": "07_chariot.jpg", "Сила": "08_strength.jpg",
        "Отшельник": "09_hermit.jpg", "Колесо Фортуны": "10_wheel_of_fortune.jpg",
        "Справедливость": "11_justice.jpg", "Повешенный": "12_hanged_man.jpg", "Смерть": "13_death.jpg",
        "Умеренность": "14_temperance.jpg", "Дьявол": "15_devil.jpg", "Башня": "16_tower.jpg",
        "Звезда": "17_star.jpg", "Луна": "18_moon.jpg", "Солнце": "19_sun.jpg",
        "Суд": "20_judgment.jpg", "Мир": "21_world.jpg"
    }
    filename = CARD_IMAGE_FILES.get(card_name)
    if filename:
        path = os.path.join("tarot_cards", filename)
        if os.path.exists(path):
            return path
    return None

# ============================================================================
# 🔧 НОВЫЕ ФУНКЦИИ ДЛЯ ОПЛАТЫ СБП (Альфа-Бизнес API) - БЕЗ ВЕБХУКА
# ============================================================================

ALPHA_API_URL = "https://business.alfa.ru/api/v2"
ALPHA_TEST_URL = "https://test-business.alfa.ru/api/v2"

def get_alpha_api_url():
    test_mode = os.getenv("ALPHA_TEST_MODE", "true").lower() == "true"
    return ALPHA_TEST_URL if test_mode else ALPHA_API_URL

def generate_payment_id(user_id, amount):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    data = f"{user_id}_{amount}_{timestamp}"
    return hashlib.md5(data.encode()).hexdigest()[:32]

def generate_sign(data, secret_key):
    sorted_data = "&".join([f"{k}={v}" for k, v in sorted(data.items())])
    sign = hmac.new(
        secret_key.encode(),
        sorted_data.encode(),
        hashlib.sha256
    ).hexdigest()
    return sign.upper()

async def create_sbp_payment(user_id, amount_rub, pack_size):
    client_id = os.getenv("ALPHA_CLIENT_ID")
    secret_key = os.getenv("ALPHA_SECRET_KEY")
    merchant_id = os.getenv("ALPHA_MERCHANT_ID")
    
    if not all([client_id, secret_key, merchant_id]):
        print("❌ Не настроены credentials Альфа-Бизнес")
        return None
    
    payment_id = generate_payment_id(user_id, amount_rub)
    api_url = get_alpha_api_url()
    
    request_data = {
        "merchantId": merchant_id,
        "paymentId": payment_id,
        "amount": str(amount_rub),
        "currency": "RUB",
        "description": f"Пакет раскладов Таро ({pack_size} шт.)",
        "expiration": (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S"),
        "callbackUrl": ""
    }
    
    sign = generate_sign(request_data, secret_key)
    request_data["signature"] = sign
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_url}/sbp/payment",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                
                if response.status == 200 and result.get("success"):
                    create_payment(
                        user_id=user_id,
                        amount_rub=amount_rub,
                        pack_size=pack_size,
                        payment_id=payment_id,
                        crypto_currency="SBP",
                        crypto_amount=0
                    )
                    
                    return {
                        "payment_id": payment_id,
                        "payment_url": result.get("paymentUrl"),
                        "qr_code": result.get("qrCode"),
                        "amount": amount_rub,
                        "pack_size": pack_size
                    }
                else:
                    print(f"❌ Ошибка создания платежа: {result}")
                    return None
                    
    except Exception as e:
        print(f"❌ Ошибка подключения к API Альфа: {e}")
        return None

async def check_payment_status(payment_id):
    client_id = os.getenv("ALPHA_CLIENT_ID")
    secret_key = os.getenv("ALPHA_SECRET_KEY")
    merchant_id = os.getenv("ALPHA_MERCHANT_ID")
    
    if not all([client_id, secret_key, merchant_id]):
        return None
    
    api_url = get_alpha_api_url()
    
    request_data = {
        "merchantId": merchant_id,
        "paymentId": payment_id
    }
    
    sign = generate_sign(request_data, secret_key)
    request_data["signature"] = sign
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_url}/sbp/status",
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    status = result.get("status")
                    
                    if status == "PAID":
                        user_id, pack_size = complete_payment(payment_id, "SBP")
                        if user_id and pack_size:
                            print(f"✅ Платёж {payment_id} обработан. Пользователь {user_id} получил {pack_size} раскладов.")
                    
                    return {
                        "payment_id": payment_id,
                        "status": status,
                        "amount": result.get("amount"),
                        "paid_at": result.get("paidAt")
                    }
                else:
                    print(f"❌ Ошибка проверки статуса: {result}")
                    return None
                    
    except Exception as e:
        print(f"❌ Ошибка проверки статуса: {e}")
        return None

# ============================================================================
# ДАННЫЕ КАРТ ТАРО (22 Старших Аркана)
# ============================================================================

MAJOR_ARCANA = {
    "Шут": {
        "short": "Новые начинания, спонтанность, вера в будущее",
        "love": "Новые романтические знакомства, спонтанные отношения, беззаботность в любви",
        "career": "Начало нового проекта, творческий подход, готовность рисковать",
        "advice": "Доверяйте своей интуиции и внутреннему голосу. Не бойтесь начинать с чистого листа — вселенная поддерживает смелые шаги."
    },
    "Маг": {
        "short": "Сила воли, творчество, манифестация желаний",
        "love": "Харизма и обаяние притягивают партнёров, умение создавать волшебство в отношениях",
        "career": "Успешные переговоры, реализация амбициозных планов, лидерство",
        "advice": "Вы обладаете всеми инструментами для достижения целей. Используйте свои таланты осознанно и с фокусом."
    },
    "Жрица": {
        "short": "Интуиция, тайные знания, внутренняя мудрость",
        "love": "Глубокая эмоциональная связь, интуитивное понимание партнёра без слов",
        "career": "Аналитический подход, работа с конфиденциальной информацией",
        "advice": "Прислушайтесь к внутреннему голосу — он знает ответы раньше разума. Медитация и тишина помогут услышать мудрость души."
    },
    "Императрица": {
        "short": "Изобилие, материнство, творческое начало",
        "love": "Гармония и забота в отношениях, плодотворный союз, нежность",
        "career": "Рост и развитие проектов, творческая реализация, изобилие ресурсов",
        "advice": "Будьте щедры и открыты к миру. Заботьтесь о себе и других с любовью. Творчество — ваш путь к изобилию."
    },
    "Император": {
        "short": "Структура, власть, стабильность, дисциплина",
        "love": "Надёжность и защита в отношениях, ответственность за партнёра",
        "career": "Лидерство, организация, достижение целей через дисциплину",
        "advice": "Создайте порядок в жизни — структура даёт свободу. Берите ответственность за свои решения."
    },
    "Жрец": {
        "short": "Духовное руководство, традиции, учение",
        "love": "Духовная связь с партнёром, традиционные ценности в отношениях",
        "career": "Наставничество, обучение других, следование правилам профессии",
        "advice": "Ищите мудрость у опытных людей, но фильтруйте через своё сердце. Следуйте традициям, которые ведут к свету."
    },
    "Влюблённые": {
        "short": "Выбор, гармония, глубокая связь",
        "love": "Любовь как высшее проявление души, важный выбор в отношениях",
        "career": "Выбор жизненного пути, сотрудничество, гармония в коллективе",
        "advice": "Слушайте сердце, но не игнорируйте разум. Выбор, который вы делаете сегодня, определит вашу судьбу завтра."
    },
    "Колесница": {
        "short": "Победа, воля, движение вперёд",
        "love": "Страстные отношения, преодоление трудностей вместе",
        "career": "Успех, продвижение, достижение целей через упорство",
        "advice": "Контролируйте свои эмоции — они ваша колесница. Двигайтесь к цели с уверенностью."
    },
    "Сила": {
        "short": "Внутренняя сила, мягкость, контроль над эмоциями",
        "love": "Терпение и сострадание в отношениях, эмоциональная зрелость",
        "career": "Управление стрессом, мягкая сила в переговорах",
        "advice": "Используйте мягкость вместо силы — она сильнее стали. Контролируйте свои страхи, а не обстоятельства."
    },
    "Отшельник": {
        "short": "Самопознание, мудрость, уединение",
        "love": "Пауза в отношениях для поиска себя, мудрость в выборе партнёра",
        "career": "Анализ и планирование в одиночестве, работа над собой",
        "advice": "Время для размышлений — не бегите от одиночества. Ищите ответы внутри себя, а не в одобрении других."
    },
    "Колесо Фортуны": {
        "short": "Перемены, удача, циклы жизни",
        "love": "Неожиданные повороты в отношениях, судьбоносная встреча",
        "career": "Перемены на работе, удачный поворот событий",
        "advice": "Примите перемены как часть жизненного цикла. Когда колесо вращается вниз — наберитесь терпения. Когда вверх — действуйте смело."
    },
    "Справедливость": {
        "short": "Баланс, честность, карма",
        "love": "Честность в отношениях, справедливое решение конфликтов",
        "career": "Честная оценка, юридические вопросы",
        "advice": "Будьте честны с собой и другими — вселенная возвращает всё бумерангом. Взвешивайте решения на весах разума и сердца."
    },
    "Повешенный": {
        "short": "Жертва, новый взгляд, пауза",
        "love": "Переоценка отношений, временное затишье для осознания чувств",
        "career": "Пауза в проекте для нового видения",
        "advice": "Иногда нужно остановиться, чтобы увидеть полную картину. Отпустите контроль — в бездействии рождается прозрение."
    },
    "Смерть": {
        "short": "Преобразование, конец цикла, возрождение",
        "love": "Конец старых отношений для начала нового этапа",
        "career": "Завершение проекта, кардинальные изменения",
        "advice": "Отпустите старое, чтобы освободить место новому. Смерть — не конец, а трансформация."
    },
    "Умеренность": {
        "short": "Баланс, гармония, терпение",
        "love": "Гармония в отношениях, баланс между личными границами и близостью",
        "career": "Баланс работы и жизни, терпение в достижении целей",
        "advice": "Ищите золотую середину во всём. Смешивайте противоположности — в их союзе рождается гармония."
    },
    "Дьявол": {
        "short": "Искушение, зависимости, материальные цепи",
        "love": "Токсичные отношения, зависимость от партнёра",
        "career": "Материальные привязанности, работа ради денег",
        "advice": "Освободитесь от того, что держит вас в плену — страхи, зависимости, иллюзии. Цепи часто существуют только в вашем сознании."
    },
    "Башня": {
        "short": "Неожиданные изменения, разрушение старого",
        "love": "Разрыв отношений, неожиданные открытия",
        "career": "Увольнение, кризис, разрушение старых структур",
        "advice": "Примите неизбежное — иногда нужно разрушить старое, чтобы построить новое. После обвала Башни небо становится ближе."
    },
    "Звезда": {
        "short": "Надежда, вдохновение, духовное исцеление",
        "love": "Идеализация партнёра, духовная связь",
        "career": "Вдохновение, творческий прорыв",
        "advice": "Верьте в лучшее, даже когда всё кажется безнадёжным. Ваша надежда — маяк для других."
    },
    "Луна": {
        "short": "Иллюзии, подсознание, тайны",
        "love": "Недопонимание, скрытые чувства, интуиция о партнёре",
        "career": "Неопределённость, скрытые мотивы коллег",
        "advice": "Доверяйте интуиции, но проверяйте факты. Луна показывает отражение, а не истину."
    },
    "Солнце": {
        "short": "Успех, радость, ясность",
        "love": "Счастливые отношения, радость и ясность чувств",
        "career": "Успех, признание, ясность в целях",
        "advice": "Наслаждайтесь моментом — вы на правильном пути. Ваша искренность притягивает удачу."
    },
    "Суд": {
        "short": "Пробуждение, возрождение, призыв к действию",
        "love": "Пробуждение чувств, новый этап в отношениях",
        "career": "Призыв к переменам, новое начало",
        "advice": "Пришло время действовать — не откладывайте. Подведите итоги прошлого, но не живите в нём."
    },
    "Мир": {
        "short": "Завершение, гармония, достижение цели",
        "love": "Гармония в отношениях, завершение цикла",
        "career": "Завершение проекта, достижение цели",
        "advice": "Вы достигли цели — наслаждайтесь результатом. Но помните: каждый конец — это новое начало."
    }
}

def get_random_cards(count=3):
    if count > len(MAJOR_ARCANA):
        count = len(MAJOR_ARCANA)
    cards = random.sample(list(MAJOR_ARCANA.keys()), count)
    return [(card, MAJOR_ARCANA[card]) for card in cards]

def get_spread_options():
    return {
        'past_present_future': {
            'name': '🎴 Прошлое-Настоящее-Будущее',
            'description': '🔮 Классический расклад, показывающий динамику вашей ситуации во времени.\nПомогает увидеть корни проблемы, текущее состояние и возможное развитие событий.',
            'cards_count': 3,
            'positions': ["🎴 ПРОШЛОЕ", "🎴 НАСТОЯЩЕЕ", "🎴 БУДУЩЕЕ"]
        },
        'celtic_cross': {
            'name': '⚔️ Кельтский крест (10 карт)',
            'description': '🔮 Самый глубокий и многогранный расклад в Таро.\nАнализирует ситуацию со всех сторон: сознание, подсознание, прошлое, будущее, внутренние и внешние влияния.\nИдеален для сложных жизненных вопросов.',
            'cards_count': 10,
            'positions': [
                "🎴 ТЕКУЩАЯ СИТУАЦИЯ", "🎴 ПРЕПЯТСТВИЕ", "🎴 СОЗНАНИЕ",
                "🎴 БЕССОЗНАТЕЛЬНОЕ", "🎴 ПРОШЛОЕ", "🎴 БУДУЩЕЕ",
                "🎴 ВАШ ПОДХОД", "🎴 ВНЕШНЕЕ ВЛИЯНИЕ", "🎴 НАДЕЖДЫ И СТРАХИ",
                "🎴 ИТОГОВЫЙ РЕЗУЛЬТАТ"
            ]
        },
        'relationship': {
            'name': '❤️‍🔥 Расклад на отношения',
            'description': '🔮 Специализированный расклад для анализа любовных и близких отношений.\nПоказывает энергию обоих партнёров, динамику связи и скрытые препятствия.\nПомогает понять, куда движутся отношения.',
            'cards_count': 5,
            'positions': [
                "🎴 ВАША ЭНЕРГИЯ В ОТНОШЕНИЯХ", "🎴 ЭНЕРГИЯ ПАРТНЁРА",
                "🎴 ДИНАМИКА СВЯЗИ", "🎴 СКРЫТЫЕ ПРЕПЯТСТВИЯ",
                "🎴 СОВЕТ ТАРО ДЛЯ ГАРМОНИИ"
            ]
        },
        'career': {
            'name': '💼 Расклад на карьеру',
            'description': '🔮 Профессиональный расклад для анализа карьерного пути и финансовой ситуации.\nВыявляет скрытые возможности, препятствия и даёт стратегические рекомендации.\nПомогает принять важные решения в работе.',
            'cards_count': 4,
            'positions': [
                "🎴 ТЕКУЩАЯ ПРОФЕССИОНАЛЬНАЯ СИТУАЦИЯ",
                "🎴 СКРЫТЫЕ ВОЗМОЖНОСТИ И РЕСУРСЫ",
                "🎴 ГЛАВНЫЕ ПРЕПЯТСТВИЯ НА ПУТИ",
                "🎴 СТРАТЕГИЧЕСКАЯ РЕКОМЕНДАЦИЯ"
            ]
        },
        'daily': {
            'name': '🌅 Карта дня',
            'description': '🔮 Ежедневная карта-совет, сопровождающая вас весь день.\nДаёт ключевую энергию и ориентир для принятия решений сегодня.',
            'cards_count': 1,
            'positions': ["🎴 СОВЕТ НА СЕГОДНЯ"]
        }
    }

def format_daily_card(card_name, interpretation, user_name="Друг"):
    result = f"🌅 ВАША КАРТА ДНЯ, {user_name}! 🌅\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    result += f"✨ КАРТА: {card_name}\n"
    result += f"💫 ГЛУБИННОЕ ЗНАЧЕНИЕ:\n{interpretation['short']}\n\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    result += "🌟 СОВЕТ ТАРО НА СЕГОДНЯ 🌟\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    result += f"{interpretation['advice']}\n\n"
    result += "💫 Эта карта сопровождает вас весь день.\n"
    result += "Прислушайтесь к её посланию в ключевые моменты!\n"
    return result

def format_reading_intro(spread_id, user_name):
    spreads = get_spread_options()
    spread = spreads.get(spread_id, {})
    result = f"🔮 {spread['name'].upper()} 🔮\n"
    result += f"✨ Персонализированный расклад для {user_name}\n\n"
    result += f"💫 {spread['description']}\n\n"
    result += "👇 Нажмите «Далее», чтобы увидеть карты и их значения:"
    return result

def format_reading_cards(cards, user_name, positions, spread_id):
    if len(positions) != len(cards):
        raise ValueError(f"Несоответствие позиций ({len(positions)}) и карт ({len(cards)})")
    result = f"🎴 КАРТЫ РАСКЛАДА ДЛЯ {user_name.upper()}\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (pos, (name, interpretation)) in enumerate(zip(positions, cards)):
        result += f"{pos}\n"
        result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        result += f"✨ КАРТА: {name}\n"
        result += f"💫 ГЛУБИННОЕ ЗНАЧЕНИЕ:\n{interpretation['short']}\n\n"
        
        if spread_id in ['celtic_cross', 'past_present_future']:
            pass
        elif spread_id == 'relationship':
            result += f"❤️‍🔥 В ЛЮБВИ И ОТНОШЕНИЯХ:\n{interpretation['love']}\n\n"
        elif spread_id == 'career':
            result += f"💼 В КАРЬЕРЕ И ДЕНЬГАХ:\n{interpretation['career']}\n\n"
        else:
            result += f"❤️‍🔥 В ЛЮБВИ: {interpretation['love']}\n"
            result += f"💼 В КАРЬЕРЕ: {interpretation['career']}\n\n"

    result += "\n👇 Нажмите «Далее», чтобы получить персональный совет от Таро:"
    return result

def format_reading_advice(cards, spread_id):
    card_names = [card[0] for card in cards]
    result = "🌟 ПЕРСОНАЛЬНЫЙ СОВЕТ ТАРО 🌟\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    if spread_id in ['celtic_cross', 'past_present_future']:
        advice_parts = []
        if "Шут" in card_names or "Маг" in card_names:
            advice_parts.append("✨ Вы находитесь на пороге новых возможностей. Доверяйте своей интуиции и не бойтесь делать первый шаг — вселенная поддерживает ваши начинания.")
        if "Сила" in card_names or "Отшельник" in card_names:
            advice_parts.append("💫 Сейчас важнее всего внутренняя работа. Уделите время саморефлексии, медитации или ведению дневника. Ответы уже внутри вас.")
        if "Колесница" in card_names or "Император" in card_names:
            advice_parts.append("🔥 Ваша сила — в дисциплине и целеустремлённости. Составьте чёткий план действий и следуйте ему, несмотря на препятствия.")
        if "Луна" in card_names or "Башня" in card_names:
            advice_parts.append("🌙 Будьте готовы к неожиданным переменам и проявлению скрытых истин. Не цепляйтесь за старое — иногда разрушение необходимо для нового роста.")
        if "Солнце" in card_names or "Звезда" in card_names:
            advice_parts.append("☀️ Вас ждёт период света, радости и гармонии. Радуйтесь мелочам, делитесь своей энергией с близкими.")
        if "Суд" in card_names or "Мир" in card_names:
            advice_parts.append("🎉 Вы завершаете важный цикл в жизни. Подведите итоги, поблагодарите за опыт и смело открывайте новую главу.")
        if not advice_parts:
            advice_parts.append("💫 Помните: карты Таро показывают не предопределённое будущее, а возможности и потенциал текущего момента. Выбор всегда остаётся за вами.")
        result += "\n\n".join(advice_parts)
    elif spread_id == 'relationship':
        advice_parts = []
        if "Влюблённые" in card_names:
            advice_parts.append("❤️‍🔥 Ваши отношения находятся в гармоничной фазе. Доверяйте своей интуиции и открыто выражайте чувства.")
        if "Повешенный" in card_names or "Отшельник" in card_names:
            advice_parts.append("💫 Возможно, вам или вашему партнёру нужно время для себя. Не торопите события — дайте отношениям «дозреть».")
        if "Башня" in card_names or "Смерть" in card_names:
            advice_parts.append("🌙 Отношения проходят через трансформацию. Не цепляйтесь за старые шаблоны и ожидания.")
        if "Солнце" in card_names or "Звезда" in card_names:
            advice_parts.append("☀️ Вас ждёт период гармонии, взаимопонимания и радости в отношениях.")
        if "Дьявол" in card_names:
            advice_parts.append("⚠️ Обратите внимание на токсичные паттерны в отношениях. Освободитесь от того, что держит вас в плену.")
        if not advice_parts:
            advice_parts.append("💫 Отношения — это зеркало вашей души и путь к самопознанию. Доверяйте своей интуиции, будьте честны с собой и партнёром.")
        result += "\n\n".join(advice_parts)
    elif spread_id == 'career':
        advice_parts = []
        if "Маг" in card_names or "Император" in card_names:
            advice_parts.append("💼 Вы обладаете всеми ресурсами и талантами для профессионального успеха. Действуйте уверенно.")
        if "Колесница" in card_names or "Сила" in card_names:
            advice_parts.append("🚀 Ваша целеустремлённость и внутренняя сила приведут к успеху. Не сдавайтесь перед препятствиями.")
        if "Отшельник" in card_names or "Повешенный" in card_names:
            advice_parts.append("💫 Возможно, вам нужно время для анализа и переоценки карьерных целей.")
        if "Башня" in card_names or "Смерть" in card_names:
            advice_parts.append("🌙 Карьера проходит через важную трансформацию. Не бойтесь перемен.")
        if "Солнце" in card_names or "Звезда" in card_names:
            advice_parts.append("☀️ Вас ждёт период профессионального роста, признания и успеха.")
        if "Дьявол" in card_names:
            advice_parts.append("⚠️ Обратите внимание на баланс между работой и личной жизнью.")
        if not advice_parts:
            advice_parts.append("💫 Карьера — это путь самореализации и выражения ваших талантов миру. Верьте в себя!")
        result += "\n\n".join(advice_parts)
    else:
        if "Шут" in card_names or "Маг" in card_names:
            result += "✨ Доверяйте интуиции — новые возможности уже на подходе!"
        elif "Сила" in card_names or "Отшельник" in card_names:
            result += "💫 Время для внутренней работы — ответы внутри вас."
        elif "Колесница" in card_names or "Император" in card_names:
            result += "🔥 Дисциплина и целеустремлённость приведут к успеху."
        elif "Луна" in card_names or "Башня" in card_names:
            result += "🌙 Примите перемены — за разрушением следует рост."
        elif "Солнце" in card_names or "Звезда" in card_names:
            result += "☀️ Вас ждёт период света и гармонии — радуйтесь!"
        elif "Суд" in card_names or "Мир" in card_names:
            result += "🎉 Вы завершаете важный цикл — готовьтесь к новому началу."
        else:
            result += "💫 Доверяйте себе — вы сильнее, чем думаете!"
    result += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    result += "⚠️ ВАЖНО:\n"
    result += "Таро показывает возможные сценарии и энергии момента,\n"
    result += "но НЕ предсказывает неизбежное будущее.\n"
    result += "Ваш выбор, действия и отношение формируют реальность.\n"
    result += "Используйте расклад как инструмент рефлексии, а не как приговор.\n"
    result += "Вы — творец своей жизни! 💫\n"
    return result

def format_reading(cards, user_name="Друг", positions=None, spread_id=None):
    if positions is None:
        count = len(cards)
        if count == 1:
            positions = ["🎴 СОВЕТ НА СЕГОДНЯ"]
        elif count == 3:
            positions = ["🎴 ПРОШЛОЕ", "🎴 НАСТОЯЩЕЕ", "🎴 БУДУЩЕЕ"]
        elif count == 4:
            positions = ["🎴 ТЕКУЩАЯ СИТУАЦИЯ", "🎴 ВОЗМОЖНОСТИ", "🎴 ПРЕПЯТСТВИЯ", "🎴 РЕКОМЕНДАЦИЯ"]
        elif count == 5:
            positions = ["🎴 ВАША ЭНЕРГИЯ", "🎴 ЭНЕРГИЯ ПАРТНЁРА", "🎴 ДИНАМИКА СВЯЗИ", "🎴 ПРЕПЯТСТВИЯ", "🎴 СОВЕТ ТАРО"]
        elif count == 10:
            positions = [
                "🎴 ТЕКУЩАЯ СИТУАЦИЯ", "🎴 ПРЕПЯТСТВИЕ", "🎴 СОЗНАНИЕ",
                "🎴 БЕССОЗНАТЕЛЬНОЕ", "🎴 ПРОШЛОЕ", "🎴 БУДУЩЕЕ",
                "🎴 ВАШ ПОДХОД", "🎴 ВНЕШНЕЕ ВЛИЯНИЕ", "🎴 НАДЕЖДЫ И СТРАХИ",
                "🎴 ИТОГОВЫЙ РЕЗУЛЬТАТ"
            ]
        else:
            positions = [f"🎴 КАРТА {i+1}" for i in range(count)]
    result = f"🔮 ПЕРСОНАЛИЗИРОВАННЫЙ РАСКЛАД ДЛЯ {user_name.upper()} 🔮\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (pos, (name, interpretation)) in enumerate(zip(positions, cards)):
        result += f"{pos}\n"
        result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        result += f"✨ КАРТА: {name}\n"
        result += f"💫 ГЛУБИННОЕ ЗНАЧЕНИЕ:\n{interpretation['short']}\n\n"
        if spread_id not in ['celtic_cross', 'past_present_future']:
            if spread_id == 'relationship':
                result += f"❤️‍🔥 В ЛЮБВИ И ОТНОШЕНИЯХ:\n{interpretation['love']}\n\n"
            elif spread_id == 'career':
                result += f"💼 В КАРЬЕРЕ И ДЕНЬГАХ:\n{interpretation['career']}\n\n"
            else:
                result += f"❤️‍🔥 В ЛЮБВИ: {interpretation['love']}\n"
                result += f"💼 В КАРЬЕРЕ: {interpretation['career']}\n\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    result += "🌟 СОВЕТ ТАРО 🌟\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    result += "💫 Доверяйте своей интуиции. Вы сильнее, чем думаете!\n"
    result += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    result += "🌙 Таро — инструмент самопознания 💫\n"
    return result


# ============================================================================
# 🔧 АДМИН-ПАНЕЛЬ - ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def get_all_users(limit=100):
    """Получить список всех пользователей (для админа)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, username, first_name, balance, created_at 
        FROM users 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (limit,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_total_users_count():
    """Получить общее количество пользователей"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_total_readings_count():
    """Получить общее количество сделанных раскладов"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(total_readings) FROM reading_stats')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else 0

def get_user_by_username(username):
    """Найти пользователя по username (для админа)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, first_name, balance FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            'user_id': result[0],
            'username': result[1],
            'first_name': result[2],
            'balance': result[3]
        }
    return None



# ============================================================================
# 🔧 АДМИН-ПАНЕЛЬ - ФУНКЦИИ БЛОКИРОВКИ
# ============================================================================

def ban_user(user_id):
    """Заблокировать пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET banned = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def unban_user(user_id):
    """Разблокировать пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET banned = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def is_banned(user_id):
    """Проверить, заблокирован ли пользователь"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT banned FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else False

def set_balance(user_id, amount):
    """Установить баланс (не добавить, а именно установить)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0