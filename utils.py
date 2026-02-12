import sqlite3
import random
import re
from datetime import datetime, timedelta

# === РАБОТА С БАЗОЙ ДАННЫХ ===

def init_db():
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
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
    
    # Таблица рефералов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица сохранённых раскладов
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
    
    # Таблица платежей
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
    
    # Таблица данных пользователя (имя, дата рождения)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_data (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            birthdate TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица для отслеживания карты дня
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
    """Добавить пользователя в базу"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, balance) VALUES (?, ?, ?, 1)', (user_id, username, first_name))
    conn.commit()
    conn.close()

def get_balance(user_id):
    """Получить текущий баланс пользователя"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 1

def decrease_balance(user_id, amount=1):
    """Уменьшить баланс на указанное количество"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?', (amount, user_id, amount))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def increase_balance(user_id, amount=1):
    """Увеличить баланс на указанное количество"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def add_referral(referrer_id, referred_id):
    """Добавить реферала (+1 к балансу реферера)"""
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
    """Отметить подписку на канал (+3 к балансу)"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET subscribed = 1, balance = balance + 3 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True

def check_subscribed(user_id):
    """Проверить, подписан ли пользователь на канал"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT subscribed FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_saved_slots(user_id):
    """Получить список занятых ячеек пользователя"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT slot, timestamp FROM saved_readings WHERE user_id = ? ORDER BY slot ASC', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return {row[0]: row[1][:16] for row in results}

def save_reading(user_id, cards, interpretation, slot=None):
    """Сохранить расклад в ячейку"""
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
    """Получить сохранённый расклад из ячейки"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT cards, interpretation, timestamp FROM saved_readings WHERE user_id = ? AND slot = ?', (user_id, slot))
    result = cursor.fetchone()
    conn.close()
    return result

def delete_saved_reading(user_id, slot):
    """Удалить расклад из ячейки"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM saved_readings WHERE user_id = ? AND slot = ?', (user_id, slot))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def create_payment(user_id, amount_rub, pack_size, payment_id, crypto_currency, crypto_amount):
    """Создать запись о платеже"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO payments (user_id, amount_rub, pack_size, payment_id, crypto_currency, crypto_amount)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, amount_rub, pack_size, payment_id, crypto_currency, crypto_amount))
    conn.commit()
    conn.close()

def complete_payment(payment_id, tx_hash):
    """Завершить платёж и начислить баланс"""
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
    """Сохранить/обновить данные пользователя"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_data (user_id, name, birthdate, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, name, birthdate))
    conn.commit()
    conn.close()

def get_user_data(user_id):
    """Получить данные пользователя"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, birthdate FROM user_data WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {'name': result[0], 'birthdate': result[1]}
    return None

def get_referral_count(user_id):
    """Получить количество рефералов пользователя"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# === ФУНКЦИИ ДЛЯ КАРТЫ ДНЯ ===

def can_get_daily_card(user_id):
    """Проверить, может ли пользователь получить карту дня сегодня"""
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
    """Сохранить карту дня для пользователя"""
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
    """Получить карту дня пользователя (если есть на сегодня)"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    today = datetime.now().date().isoformat()
    cursor.execute('SELECT card_name, interpretation FROM daily_card WHERE user_id = ? AND last_used = ?', (user_id, today))
    result = cursor.fetchone()
    conn.close()
    return result if result else None

# === КАРТЫ ТАРО ===

MAJOR_ARCANA = {
    "Шут": {
        "short": "Новые начинания, спонтанность, вера в будущее",
        "love": "Новые отношения, романтическое приключение, беззаботность",
        "career": "Новый проект, риск, нестандартное решение",
        "advice": "Доверяйте интуиции, не бойтесь начинать с чистого листа"
    },
    "Маг": {
        "short": "Сила воли, творчество, манифестация желаний",
        "love": "Харизма, обаяние, способность привлекать партнёров",
        "career": "Успешные переговоры, реализация планов, лидерство",
        "advice": "Используйте все доступные ресурсы, действуйте уверенно"
    },
    "Жрица": {
        "short": "Интуиция, тайные знания, внутренняя мудрость",
        "love": "Глубокая связь, интуитивное понимание партнёра",
        "career": "Аналитический подход, работа с информацией",
        "advice": "Прислушайтесь к внутреннему голосу, доверяйте интуиции"
    },
    "Императрица": {
        "short": "Изобилие, материнство, творческое начало",
        "love": "Гармония, забота, плодотворные отношения",
        "career": "Рост, развитие, творческая реализация",
        "advice": "Будьте щедры и открыты, заботьтесь о себе и других"
    },
    "Император": {
        "short": "Структура, власть, стабильность",
        "love": "Надёжность, защита, ответственность",
        "career": "Лидерство, организация, достижение целей",
        "advice": "Создайте порядок в жизни, берите ответственность"
    },
    "Жрец": {
        "short": "Духовное руководство, традиции, учение",
        "love": "Духовная связь, традиционные ценности",
        "career": "Наставничество, обучение, следование правилам",
        "advice": "Ищите мудрость у опытных людей, следуйте традициям"
    },
    "Влюблённые": {
        "short": "Выбор, гармония, глубокая связь",
        "love": "Любовь, партнёрство, важный выбор в отношениях",
        "career": "Выбор пути, сотрудничество, гармония в коллективе",
        "advice": "Слушайте сердце, выбирайте с любовью"
    },
    "Колесница": {
        "short": "Победа, воля, движение вперёд",
        "love": "Страстные отношения, преодоление препятствий вместе",
        "career": "Успех, продвижение, достижение целей",
        "advice": "Контролируйте эмоции, двигайтесь к цели с уверенностью"
    },
    "Сила": {
        "short": "Внутренняя сила, мягкость, контроль над эмоциями",
        "love": "Терпение, сострадание, эмоциональная зрелость",
        "career": "Управление стрессом, мягкая сила в переговорах",
        "advice": "Используйте мягкость вместо силы, контролируйте страхи"
    },
    "Отшельник": {
        "short": "Самопознание, мудрость, уединение",
        "love": "Пауза в отношениях, поиск себя",
        "career": "Анализ, планирование, работа в одиночестве",
        "advice": "Время для размышлений, ищите ответы внутри себя"
    },
    "Колесо Фортуны": {
        "short": "Перемены, удача, циклы жизни",
        "love": "Неожиданные повороты, судьбоносная встреча",
        "career": "Перемены на работе, удачный поворот событий",
        "advice": "Примите перемены, это часть жизненного цикла"
    },
    "Справедливость": {
        "short": "Баланс, честность, карма",
        "love": "Честность в отношениях, справедливое решение",
        "career": "Честная оценка, юридические вопросы",
        "advice": "Будьте честны с собой и другими, всё вернётся"
    },
    "Повешенный": {
        "short": "Жертва, новый взгляд, пауза",
        "love": "Переоценка отношений, временное затишье",
        "career": "Пауза в проекте, новый взгляд на ситуацию",
        "advice": "Иногда нужно остановиться, чтобы увидеть полную картину"
    },
    "Смерть": {
        "short": "Преобразование, конец цикла, возрождение",
        "love": "Конец старых отношений, начало нового этапа",
        "career": "Завершение проекта, кардинальные изменения",
        "advice": "Отпустите старое, чтобы освободить место новому"
    },
    "Умеренность": {
        "short": "Баланс, гармония, терпение",
        "love": "Гармония в отношениях, баланс между партнёрами",
        "career": "Баланс работы и жизни, терпение в достижении целей",
        "advice": "Ищите золотую середину во всём"
    },
    "Дьявол": {
        "short": "Искушение, зависимости, материальные цепи",
        "love": "Токсичные отношения, зависимость от партнёра",
        "career": "Материальные привязанности, работа ради денег",
        "advice": "Освободитесь от того, что держит вас в плену"
    },
    "Башня": {
        "short": "Неожиданные изменения, разрушение старого",
        "love": "Разрыв отношений, неожиданные открытия",
        "career": "Увольнение, кризис, разрушение старых структур",
        "advice": "Примите неизбежное, после разрушения приходит обновление"
    },
    "Звезда": {
        "short": "Надежда, вдохновение, духовное исцеление",
        "love": "Идеализация партнёра, духовная связь",
        "career": "Вдохновение, творческий прорыв",
        "advice": "Верьте в лучшее, следуйте за своей звездой"
    },
    "Луна": {
        "short": "Иллюзии, подсознание, тайны",
        "love": "Недопонимание, скрытые чувства, интуиция",
        "career": "Неопределённость, скрытые мотивы коллег",
        "advice": "Доверяйте интуиции, но проверяйте факты"
    },
    "Солнце": {
        "short": "Успех, радость, ясность",
        "love": "Счастливые отношения, радость, ясность чувств",
        "career": "Успех, признание, ясность в целях",
        "advice": "Наслаждайтесь моментом, вы на правильном пути"
    },
    "Суд": {
        "short": "Пробуждение, возрождение, призыв к действию",
        "love": "Пробуждение чувств, новый этап в отношениях",
        "career": "Призыв к переменам, новое начало",
        "advice": "Пришло время действовать, не откладывайте"
    },
    "Мир": {
        "short": "Завершение, гармония, достижение цели",
        "love": "Гармония в отношениях, завершение цикла",
        "career": "Завершение проекта, достижение цели",
        "advice": "Вы достигли цели, наслаждайтесь результатом"
    }
}

def get_random_cards(count=3):
    """Получить случайные карты для расклада"""
    if count > len(MAJOR_ARCANA):
        count = len(MAJOR_ARCANA)
    cards = random.sample(list(MAJOR_ARCANA.keys()), count)
    return [(card, MAJOR_ARCANA[card]) for card in cards]

def get_spread_options():
    """Варианты раскладов"""
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
                "🎴 Ситуация", "🎴 Препятствие", "🎴 Сознание", 
                "🎴 Бессознательное", "🎴 Прошлое", "🎴 Будущее",
                "🎴 Ваш подход", "🎴 Внешнее влияние", "🎴 Надежды/страхи",
                "🎴 Итог"
            ]
        },
        'relationship': {
            'name': '❤️‍🔥 Расклад на отношения',
            'cards_count': 5,
            'positions': [
                "🎴 Вы", "🎴 Партнёр", "🎴 Отношения", 
                "🎴 Препятствия", "🎴 Совет"
            ]
        },
        'career': {
            'name': '💼 Расклад на карьеру',
            'cards_count': 4,
            'positions': [
                "🎴 Текущая работа", "🎴 Возможности", 
                "🎴 Препятствия", "🎴 Рекомендация"
            ]
        },
        'daily': {
            'name': '🌅 Карта дня',
            'cards_count': 1,
            'positions': ["🎴 СОВЕТ НА СЕГОДНЯ"]
        }
    }

def format_reading(cards, user_name="Друг", positions=None):
    """Форматирование расклада с ОДНИМ общим советом в конце"""
    if positions is None:
        positions = ["🎴 ПРОШЛОЕ", "🎴 НАСТОЯЩЕЕ", "🎴 БУДУЩЕЕ"]
    
    result = f"🔮 ПЕРСОНАЛИЗИРОВАННЫЙ РАСКЛАД ДЛЯ {user_name.upper()} 🔮\n"
    result += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for pos, (name, interpretation) in zip(positions, cards):
        result += f"{pos}\n"
        result += f"━━━━━━━━━━━━━━━━━━━━\n"
        result += f"✨ Карта: {name}\n"
        result += f"💫 Значение: {interpretation['short']}\n\n"
        result += f"❤️‍🔥 В любви: {interpretation['love']}\n"
        result += f"💼 В карьере: {interpretation['career']}\n\n"
    
    # ОДИН ОБЩИЙ СОВЕТ НА ВЕСЬ РАСКЛАД
    result += "━━━━━━━━━━━━━━━━━━━━\n"
    result += "🌟 ПЕРСОНАЛЬНЫЙ СОВЕТ ТАРО 🌟\n"
    result += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Генерируем совет на основе всех трёх карт
    card_names = [card[0] for card in cards]
    advice_parts = []
    
    if "Шут" in card_names or "Маг" in card_names:
        advice_parts.append("✨ Вы находитесь на пороге новых возможностей. Доверяйте своей интуиции и не бойтесь делать первый шаг — вселенная поддерживает ваши начинания.")
    
    if "Сила" in card_names or "Отшельник" in card_names:
        advice_parts.append("💫 Сейчас важнее всего внутренняя работа. Уделите время саморефлексии, медитации или дневнику. Ответы уже внутри вас — просто прислушайтесь.")
    
    if "Колесница" in card_names or "Император" in card_names:
        advice_parts.append("🔥 Ваша сила — в дисциплине и целеустремлённости. Составьте чёткий план действий и следуйте ему. Вы способны достичь любой цели, если сохраните фокус.")
    
    if "Луна" in card_names or "Башня" in card_names:
        advice_parts.append("🌙 Будьте готовы к неожиданным переменам. Не цепляйтесь за старое — иногда разрушение необходимо для нового роста. Доверяйте процессу.")
    
    if "Солнце" in card_names or "Звезда" in card_names:
        advice_parts.append("☀️ Вас ждёт период света и гармонии. Радуйтесь мелочам, делитесь своей энергией с близкими. Ваша искренность притягивает удачу и хороших людей.")
    
    if "Суд" in card_names or "Мир" in card_names:
        advice_parts.append("🎉 Вы завершаете важный цикл в жизни. Подведите итоги, поблагодарите за опыт и смело открывайте новую главу. Вас ждёт гармония и достижение целей.")
    
    # Если нет специфических советов — общий
    if not advice_parts:
        advice_parts.append("💫 Помните: карты показывают возможности, а выбор всегда за вами. Доверяйте себе, слушайте своё сердце и действуйте с любовью. Вы сильнее, чем думаете!")
    
    # Объединяем советы в один текст
    result += "\n".join(advice_parts)
    result += "\n\n"
    result += "🌙 Помните: Таро — это инструмент самопознания, а не предсказание судьбы.\n"
    result += "💫 Вы сами создаёте своё будущее каждым своим решением!\n"
    
    return result

def format_daily_card(card_name, interpretation, user_name="Друг"):
    """Форматирование карты дня"""
    result = f"🌅 ВАША КАРТА ДНЯ, {user_name}! 🌅\n"
    result += "━━━━━━━━━━━━━━━━━━━━\n\n"
    result += f"✨ Карта: {card_name}\n"
    result += f"💫 Значение: {interpretation['short']}\n\n"
    result += f"❤️‍🔥 В любви: {interpretation['love']}\n"
    result += f"💼 В карьере: {interpretation['career']}\n\n"
    result += "━━━━━━━━━━━━━━━━━━━━\n"
    result += "🌟 СОВЕТ НА СЕГОДНЯ 🌟\n"
    result += "━━━━━━━━━━━━━━━━━━━━\n\n"
    result += f"{interpretation['advice']}\n\n"
    result += "💫 Эта карта сопровождает вас весь день. Прислушайтесь к её посланию!\n"
    return result