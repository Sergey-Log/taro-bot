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

# ... (весь предыдущий код без изменений до функции get_spread_options) ...

def get_spread_options():
    """Варианты раскладов с уникальными описаниями"""
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

def format_reading_intro(spread_id, user_name):
    """Форматирование вводной части расклада (этап 1)"""
    spreads = get_spread_options()
    spread = spreads.get(spread_id, {})
    
    result = f"🔮 {spread['name'].upper()} 🔮\n"
    result += f"✨ Персонализированный расклад для {user_name}\n\n"
    result += f"💫 {spread['description']}\n\n"
    result += "👇 Нажмите «Далее», чтобы увидеть карты и их значения:"
    return result

def format_reading_cards(cards, user_name, positions, spread_id):
    """Форматирование карт и значений (этап 2)"""
    if len(positions) != len(cards):
        raise ValueError(f"Несоответствие позиций ({len(positions)}) и карт ({len(cards)})")
    
    result = f"🎴 КАРТЫ РАСКЛАДА ДЛЯ {user_name.upper()}\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, (pos, (name, interpretation)) in enumerate(zip(positions, cards)):
        result += f"{pos}\n"
        result += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        result += f"✨ КАРТА: {name}\n"
        result += f"💫 ГЛУБИННОЕ ЗНАЧЕНИЕ:\n{interpretation['short']}\n\n"
        
        # Чёткое разделение по типам раскладов
        if spread_id in ['celtic_cross', 'past_present_future']:
            # Только глубинное значение — без любви/карьеры
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
    """Форматирование развёрнутого совета (этап 3)"""
    card_names = [card[0] for card in cards]
    result = "🌟 ПЕРСОНАЛЬНЫЙ СОВЕТ ТАРО 🌟\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Развёрнутые советы для кельтского креста и прошлое-настоящее-будущее
    if spread_id in ['celtic_cross', 'past_present_future']:
        advice_parts = []
        
        if "Шут" in card_names or "Маг" in card_names:
            advice_parts.append("✨ Вы находитесь на пороге новых возможностей. Доверяйте своей интуиции и не бойтесь делать первый шаг — вселенная поддерживает ваши начинания. Иногда именно безрассудный прыгок в неизвестность открывает двери к самым удивительным приключениям жизни. Сохраняйте детскую искренность и открытость миру — они ваш главный ресурс сейчас.")
        
        if "Сила" in card_names or "Отшельник" in card_names:
            advice_parts.append("💫 Сейчас важнее всего внутренняя работа. Уделите время саморефлексии, медитации или ведению дневника. Ответы уже внутри вас — просто прислушайтесь к тишине своего сердца. В уединении рождается мудрость, а в тишине — ясность. Не торопитесь с решениями — дайте ситуации «дозреть».")
        
        if "Колесница" in card_names or "Император" in card_names:
            advice_parts.append("🔥 Ваша сила — в дисциплине и целеустремлённости. Составьте чёткий план действий и следуйте ему, несмотря на препятствия. Вы обладаете всем необходимым для достижения целей — верьте в себя и действуйте с уверенностью. Помните: великие империи строятся не за день, а кирпич за кирпичом. Будьте архитектором своей жизни.")
        
        if "Луна" in card_names or "Башня" in card_names:
            advice_parts.append("🌙 Будьте готовы к неожиданным переменам и проявлению скрытых истин. Не цепляйтесь за старое — иногда разрушение необходимо для нового роста. Доверяйте процессу трансформации, даже если сейчас всё кажется хаотичным. После шторма всегда наступает ясная погода. Истинная свобода приходит через принятие неизбежного.")
        
        if "Солнце" in card_names or "Звезда" in card_names:
            advice_parts.append("☀️ Вас ждёт период света, радости и гармонии. Радуйтесь мелочам, делитесь своей энергией с близкими. Ваша искренность и открытость притягивают удачу и хороших людей. Не прячьте свой свет — мир нуждается в вашем сиянии. Верьте в лучшее, даже когда обстоятельства кажутся сложными — вы сильнее, чем думаете.")
        
        if "Суд" in card_names or "Мир" in card_names:
            advice_parts.append("🎉 Вы завершаете важный цикл в жизни. Подведите итоги, поблагодарите за опыт и смело открывайте новую главу. Вас ждёт гармония, целостность и достижение долгожданной цели. Помните: каждый конец — это новое начало, а каждое завершение — повод для праздника. Вы заслужили этот момент.")
        
        if not advice_parts:
            advice_parts.append("💫 Помните: карты Таро показывают не предопределённое будущее, а возможности и потенциал текущего момента. Выбор всегда остаётся за вами. Доверяйте себе, слушайте своё сердце и действуйте с любовью и осознанностью. Вы сильнее, мудрее и способнее, чем думаете!")
        
        result += "\n\n".join(advice_parts)
    else:
        # Короткие советы для других раскладов
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