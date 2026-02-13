import sqlite3
import random
import re
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 1,
            subscribed BOOLEAN DEFAULT 0,
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
    
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, balance) VALUES (?, ?, ?, 1)', (user_id, username, first_name))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 1

def decrease_balance(user_id, amount=1):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?', (amount, user_id, amount))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def increase_balance(user_id, amount=1):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def add_referral(referrer_id, referred_id):
    conn = sqlite3.connect('tarot_bot.db')
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
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET subscribed = 1, balance = balance + 3 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True

def check_subscribed(user_id):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT subscribed FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_saved_slots(user_id):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT slot, timestamp FROM saved_readings WHERE user_id = ? ORDER BY slot ASC', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return {row[0]: row[1][:16] for row in results}

def save_reading(user_id, cards, interpretation, slot=None):
    conn = sqlite3.connect('tarot_bot.db')
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
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT cards, interpretation, timestamp FROM saved_readings WHERE user_id = ? AND slot = ?', (user_id, slot))
    result = cursor.fetchone()
    conn.close()
    return result

def delete_saved_reading(user_id, slot):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM saved_readings WHERE user_id = ? AND slot = ?', (user_id, slot))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def create_payment(user_id, amount_rub, pack_size, payment_id, crypto_currency, crypto_amount):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO payments (user_id, amount_rub, pack_size, payment_id, crypto_currency, crypto_amount)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, amount_rub, pack_size, payment_id, crypto_currency, crypto_amount))
    conn.commit()
    conn.close()

def complete_payment(payment_id, tx_hash):
    conn = sqlite3.connect('tarot_bot.db')
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
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_data (user_id, name, birthdate, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, name, birthdate))
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, birthdate FROM user_data WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {'name': result[0], 'birthdate': result[1]}
    return None

def get_referral_count(user_id):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def can_get_daily_card(user_id):
    conn = sqlite3.connect('tarot_bot.db')
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
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    today = datetime.now().date().isoformat()
    cursor.execute('''
        INSERT OR REPLACE INTO daily_card (user_id, last_used, card_name, interpretation, created_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, today, card_name, interpretation))
    conn.commit()
    conn.close()

def get_daily_card(user_id):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    today = datetime.now().date().isoformat()
    cursor.execute('SELECT card_name, interpretation FROM daily_card WHERE user_id = ? AND last_used = ?', (user_id, today))
    result = cursor.fetchone()
    conn.close()
    return result if result else None

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
            'cards_count': 3,
            'positions': ["🎴 ПРОШЛОЕ", "🎴 НАСТОЯЩЕЕ", "🎴 БУДУЩЕЕ"]
        },
        'celtic_cross': {
            'name': '⚔️ Кельтский крест (10 карт)',
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
            'cards_count': 5,
            'positions': [
                "🎴 ВАША ЭНЕРГИЯ В ОТНОШЕНИЯХ", "🎴 ЭНЕРГИЯ ПАРТНЁРА", 
                "🎴 ДИНАМИКА СВЯЗИ", "🎴 СКРЫТЫЕ ПРЕПЯТСТВИЯ", 
                "🎴 СОВЕТ ТАРО ДЛЯ ГАРМОНИИ"
            ]
        },
        'career': {
            'name': '💼 Расклад на карьеру',
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
            'cards_count': 1,
            'positions': ["🎴 СОВЕТ НА СЕГОДНЯ"]
        }
    }

def format_reading(cards, user_name="Друг", positions=None, spread_id=None):
    """Форматирование расклада с ЧЁТКИМ РАЗДЕЛЕНИЕМ по типам"""
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
    
    if len(positions) != len(cards):
        raise ValueError(f"Несоответствие позиций ({len(positions)}) и карт ({len(cards)})")
    
    result = f"🔮 ПЕРСОНАЛИЗИРОВАННЫЙ РАСКЛАД ДЛЯ {user_name.upper()} 🔮\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # ✅ ЧЁТКОЕ РАЗДЕЛЕНИЕ ПО ТИПАМ РАСКЛАДОВ:
    for i, (pos, (name, interpretation)) in enumerate(zip(positions, cards)):
        result += f"{pos}\n"
        result += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        result += f"✨ КАРТА: {name}\n"
        result += f"💫 ГЛУБИННОЕ ЗНАЧЕНИЕ:\n{interpretation['short']}\n\n"
        
        # 🔹 КЕЛЬТСКИЙ КРЕСТ и ПРОШЛОЕ-НАСТОЯЩЕЕ-БУДУЩЕЕ: ТОЛЬКО глубинное значение
        if spread_id in ['celtic_cross', 'past_present_future']:
            # НЕ добавляем разделы любви и карьеры
            pass
        
        # 🔹 РАСКЛАД НА ОТНОШЕНИЯ: ТОЛЬКО любовь
        elif spread_id == 'relationship':
            result += f"❤️‍🔥 В ЛЮБВИ И ОТНОШЕНИЯХ:\n{interpretation['love']}\n\n"
        
        # 🔹 РАСКЛАД НА КАРЬЕРУ: ТОЛЬКО карьера
        elif spread_id == 'career':
            result += f"💼 В КАРЬЕРЕ И ДЕНЬГАХ:\n{interpretation['career']}\n\n"
        
        # 🔹 ОСТАЛЬНЫЕ РАСКЛАДЫ: оба раздела
        else:
            result += f"❤️‍🔥 В ЛЮБВИ И ОТНОШЕНИЯХ:\n{interpretation['love']}\n\n"
            result += f"💼 В КАРЬЕРЕ И ДЕНЬГАХ:\n{interpretation['career']}\n\n"
    
    # ОБЩИЙ СОВЕТ
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    result += "🌟 СОВЕТ ТАРО 🌟\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    result += "💫 Доверяйте своей интуиции. Вы сильнее, чем думаете!\n"
    result += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    result += "🌙 Таро — инструмент самопознания 💫\n"
    
    return result

def format_daily_card(card_name, interpretation, user_name="Друг"):
    """Форматирование карты дня БЕЗ разделов любви и карьеры"""
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