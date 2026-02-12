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

# === РАСШИРЕННЫЕ КАРТЫ ТАРО ===

MAJOR_ARCANA = {
    "Шут": {
        "short": "Новые начинания, спонтанность, вера в будущее, свобода от ограничений",
        "love": "Новые романтические знакомства, спонтанные отношения, беззаботность и лёгкость в любви, готовность к приключениям вместе с партнёром",
        "career": "Начало нового проекта без гарантий, но с большим потенциалом, творческий подход к работе, готовность рисковать ради мечты",
        "advice": "Доверяйте своей интуиции и внутреннему голосу. Не бойтесь начинать с чистого листа — вселенная поддерживает смелые шаги. Иногда нужно прыгнуть в неизвестность, чтобы обрести крылья. Сохраняйте детскую искренность и открытость миру."
    },
    "Маг": {
        "short": "Сила воли, творчество, манифестация желаний, умение превращать идеи в реальность",
        "love": "Харизма и обаяние притягивают партнёров, умение создавать волшебство в отношениях, способность материализовать совместные мечты",
        "career": "Успешные переговоры, реализация амбициозных планов, лидерство и влияние, умение использовать все доступные ресурсы",
        "advice": "Вы обладаете всеми инструментами для достижения целей. Используйте свои таланты осознанно и с фокусом. Слова имеют силу — говорите то, что хотите создать в жизни. Будьте архитектором своей реальности, а не пассажиром."
    },
    "Жрица": {
        "short": "Интуиция, тайные знания, внутренняя мудрость, связь с подсознанием",
        "love": "Глубокая эмоциональная связь, интуитивное понимание партнёра без слов, таинственность в отношениях",
        "career": "Аналитический подход, работа с конфиденциальной информацией, интуитивные прозрения в бизнесе",
        "advice": "Прислушайтесь к внутреннему голосу — он знает ответы раньше разума. Медитация и тишина помогут услышать мудрость души. Не торопитесь с решениями — дайте интуиции проявиться. Иногда молчание говорит громче слов."
    },
    "Императрица": {
        "short": "Изобилие, материнство, творческое начало, плодородие во всех сферах жизни",
        "love": "Гармония и забота в отношениях, плодотворный союз, создание семьи, нежность и принятие",
        "career": "Рост и развитие проектов, творческая реализация, изобилие ресурсов, плодотворная работа",
        "advice": "Будьте щедры и открыты к миру. Заботьтесь о себе и других с любовью. Творчество — ваш путь к изобилию. Доверяйте естественным циклам жизни — как природа, вы тоже проходите периоды роста и отдыха. Радуйтесь простым радостям."
    },
    "Император": {
        "short": "Структура, власть, стабильность, дисциплина и порядок в жизни",
        "love": "Надёжность и защита в отношениях, ответственность за партнёра, стабильный союз",
        "career": "Лидерство, организация, достижение целей через дисциплину, построение прочного фундамента",
        "advice": "Создайте порядок в жизни — структура даёт свободу. Берите ответственность за свои решения. Будьте твёрдым, но справедливым. Помните: настоящая сила — в самодисциплине, а не в контроле над другими. Строите империю шаг за шагом."
    },
    "Жрец": {
        "short": "Духовное руководство, традиции, учение, связь с высшими силами",
        "love": "Духовная связь с партнёром, традиционные ценности в отношениях, мудрость в выборе спутника жизни",
        "career": "Наставничество, обучение других, следование правилам и традициям профессии",
        "advice": "Ищите мудрость у опытных людей, но фильтруйте через своё сердце. Следуйте традициям, которые ведут к свету. Ваша вера — источник силы. Иногда нужно остановиться и задать себе главный вопрос: «Что действительно важно?»"
    },
    "Влюблённые": {
        "short": "Выбор, гармония, глубокая связь, единство души и разума",
        "love": "Любовь как высшее проявление души, важный выбор в отношениях, гармония двух сердец",
        "career": "Выбор жизненного пути, сотрудничество, гармония в коллективе, баланс между работой и личной жизнью",
        "advice": "Слушайте сердце, но не игнорируйте разум. Выбор, который вы делаете сегодня, определит вашу судьбу завтра. Истинная любовь — это свобода выбора, а не зависимость. Доверяйте своей способности различать подлинное от иллюзорного."
    },
    "Колесница": {
        "short": "Победа, воля, движение вперёд, преодоление препятствий через силу характера",
        "love": "Страстные отношения, преодоление трудностей вместе, движение к общей цели",
        "career": "Успех, продвижение, достижение целей через упорство, управление сложными проектами",
        "advice": "Контролируйте свои эмоции — они ваша колесница. Двигайтесь к цели с уверенностью, но будьте гибкими на поворотах судьбы. Победа требует дисциплины и фокуса. Помните: настоящая сила — в умении управлять противоположными силами внутри себя."
    },
    "Сила": {
        "short": "Внутренняя сила, мягкость, контроль над эмоциями, мужество без агрессии",
        "love": "Терпение и сострадание в отношениях, эмоциональная зрелость, умение усмирять страсти любовью",
        "career": "Управление стрессом, мягкая сила в переговорах, влияние через уважение, а не страх",
        "advice": "Используйте мягкость вместо силы — она сильнее стали. Контролируйте свои страхи, а не обстоятельства. Настоящая сила рождается из принятия своей уязвимости. Дрессируйте внутреннего льва любовью, а не кнутом."
    },
    "Отшельник": {
        "short": "Самопознание, мудрость, уединение, поиск истины в тишине",
        "love": "Пауза в отношениях для поиска себя, мудрость в выборе партнёра, внутренняя работа перед новым союзом",
        "career": "Анализ и планирование в одиночестве, работа над собой как над главным проектом",
        "advice": "Время для размышлений — не бегите от одиночества. Ищите ответы внутри себя, а не в одобрении других. Зажгите внутренний фонарь — он осветит путь даже в самой густой тьме. Мудрость приходит через тишину и терпение."
    },
    "Колесо Фортуны": {
        "short": "Перемены, удача, циклы жизни, неизбежность перемен",
        "love": "Неожиданные повороты в отношениях, судьбоносная встреча, циклы сближения и отдаления",
        "career": "Перемены на работе, удачный поворот событий, циклы успеха и испытаний",
        "advice": "Примите перемены как часть жизненного цикла. Когда колесо вращается вниз — наберитесь терпения. Когда вверх — действуйте смело. Не цепляйтесь за стабильность — она иллюзорна. Единственное постоянство — это перемены."
    },
    "Справедливость": {
        "short": "Баланс, честность, карма, ответственность за свои поступки",
        "love": "Честность в отношениях, справедливое решение конфликтов, баланс между личными потребностями и потребностями партнёра",
        "career": "Честная оценка, юридические вопросы, баланс между работой и личной жизнью",
        "advice": "Будьте честны с собой и другими — вселенная возвращает всё бумерангом. Взвешивайте решения на весах разума и сердца. Примите ответственность за свои поступки — в этом сила. Справедливость не всегда приятна, но всегда необходима для роста."
    },
    "Повешенный": {
        "short": "Жертва, новый взгляд, пауза для перезагрузки, видение с другой перспективы",
        "love": "Переоценка отношений, временное затишье для осознания истинных чувств",
        "career": "Пауза в проекте для нового видения, готовность пожертвовать комфортом ради роста",
        "advice": "Иногда нужно остановиться, чтобы увидеть полную картину. Отпустите контроль — в бездействии рождается прозрение. Жертва ради высшей цели окупится сторицей. Смотрите на ситуацию с новой точки зрения — ответ уже рядом."
    },
    "Смерть": {
        "short": "Преобразование, конец цикла, возрождение через разрушение старого",
        "love": "Конец старых отношений для начала нового этапа, трансформация чувств",
        "career": "Завершение проекта, кардинальные изменения, освобождение от устаревших методов",
        "advice": "Отпустите старое, чтобы освободить место новому. Смерть — не конец, а трансформация. Не цепляйтесь за то, что уже отслужило своё. В разрушении кроется семя нового роста. Доверяйте циклам жизни — после зимы всегда приходит весна."
    },
    "Умеренность": {
        "short": "Баланс, гармония, терпение, золотая середина во всём",
        "love": "Гармония в отношениях, баланс между личными границами и близостью, терпение в развитии чувств",
        "career": "Баланс работы и жизни, терпение в достижении целей, гармония в коллективе",
        "advice": "Ищите золотую середину во всём. Смешивайте противоположности — в их союзе рождается гармония. Терпение — не пассивность, а мудрость в выборе момента. Не спешите — всё придёт в своё время. Вода точит камень не силой, а постоянством."
    },
    "Дьявол": {
        "short": "Искушение, зависимости, материальные цепи, теневая сторона личности",
        "love": "Токсичные отношения, зависимость от партнёра, страсть без любви",
        "career": "Материальные привязанности, работа ради денег, зависимость от статуса",
        "advice": "Освободитесь от того, что держит вас в плену — страхи, зависимости, иллюзии. Цепи, которые вы видите, часто существуют только в вашем сознании. Признайте свою теневую сторону — только так можно её трансформировать. Свобода начинается с осознания."
    },
    "Башня": {
        "short": "Неожиданные изменения, разрушение старого, кризис как путь к истине",
        "love": "Разрыв отношений, неожиданные открытия, разрушение иллюзий о партнёре",
        "career": "Увольнение, кризис, разрушение старых структур, необходимость начать заново",
        "advice": "Примите неизбежное — иногда нужно разрушить старое, чтобы построить новое. Кризис — это возможность увидеть правду без прикрас. После обвала Башни небо становится ближе. Не бойтесь потерять то, что уже мертво внутри вас."
    },
    "Звезда": {
        "short": "Надежда, вдохновение, духовное исцеление, вера в лучшее",
        "love": "Идеализация партнёра, духовная связь, исцеление через любовь",
        "career": "Вдохновение, творческий прорыв, вера в свой проект даже в трудные времена",
        "advice": "Верьте в лучшее, даже когда всё кажется безнадёжным. Ваша надежда — маяк для других. Следуйте за своей звездой — она ведёт к вашему предназначению. Исцеление начинается с веры в возможность исцеления. Вы — сосуд для божественного света."
    },
    "Луна": {
        "short": "Иллюзии, подсознание, тайны, интуиция в тумане",
        "love": "Недопонимание, скрытые чувства, интуиция о партнёре, иллюзии в отношениях",
        "career": "Неопределённость, скрытые мотивы коллег, работа с подсознанием клиента",
        "advice": "Доверяйте интуиции, но проверяйте факты. Луна показывает отражение, а не истину. Пройдите через туман страхов — за ним лежит ясность. Ваши сны и предчувствия содержат важные послания. Не бойтесь исследовать тёмные уголки своей души."
    },
    "Солнце": {
        "short": "Успех, радость, ясность, жизненная энергия и оптимизм",
        "love": "Счастливые отношения, радость и ясность чувств, свет в партнёрстве",
        "career": "Успех, признание, ясность в целях, энергия для достижения вершин",
        "advice": "Наслаждайтесь моментом — вы на правильном пути. Ваша искренность притягивает удачу. Будьте как ребёнок под солнцем — открыты, радостны, полны жизни. Тьма временна, а свет вечный. Делитесь своим светом с миром — он нуждается в нём."
    },
    "Суд": {
        "short": "Пробуждение, возрождение, призыв к действию, ответственность перед собой",
        "love": "Пробуждение чувств, новый этап в отношениях, осознанный выбор партнёра",
        "career": "Призыв к переменам, новое начало, ответственность за профессиональный путь",
        "advice": "Пришло время действовать — не откладывайте. Подведите итоги прошлого, но не живите в нём. Ваш внутренний голос зовёт к преображению. Ответьте на этот зов — вы готовы. Суд над вами вершит только ваша совесть. Будьте честны с собой."
    },
    "Мир": {
        "short": "Завершение, гармония, достижение цели, целостность бытия",
        "love": "Гармония в отношениях, завершение цикла, целостность в союзе двух душ",
        "career": "Завершение проекта, достижение цели, гармония между работой и жизнью",
        "advice": "Вы достигли цели — наслаждайтесь результатом. Но помните: каждый конец — это новое начало. Вы — целостны и завершены в себе. Теперь можете делиться своей мудростью с миром. Танцуйте в центре вселенной — вы её часть и одновременно её создатель."
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

# ... (начало файла без изменений) ...

def format_reading(cards, user_name="Друг", positions=None):
    """Форматирование расклада с ОДНИМ общим советом в конце"""
    if positions is None:
        # Автоматическое определение позиций по количеству карт
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
            # ✅ ИСПРАВЛЕНО: точное совпадение с 10 позициями для кельтского креста
            positions = [
                "🎴 ТЕКУЩАЯ СИТУАЦИЯ", "🎴 ПРЕПЯТСТВИЕ", "🎴 СОЗНАНИЕ", 
                "🎴 БЕССОЗНАТЕЛЬНОЕ", "🎴 ПРОШЛОЕ", "🎴 БУДУЩЕЕ",
                "🎴 ВАШ ПОДХОД", "🎴 ВНЕШНЕЕ ВЛИЯНИЕ", "🎴 НАДЕЖДЫ И СТРАХИ",
                "🎴 ИТОГОВЫЙ РЕЗУЛЬТАТ"
            ]
        else:
            positions = [f"🎴 КАРТА {i+1}" for i in range(count)]
    
    # ✅ ИСПРАВЛЕНО: проверка длины positions == длине карт
    if len(positions) != len(cards):
        raise ValueError(f"Несоответствие позиций ({len(positions)}) и карт ({len(cards)})")
    
    result = f"🔮 ПЕРСОНАЛИЗИРОВАННЫЙ РАСКЛАД ДЛЯ {user_name.upper()} 🔮\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, (pos, (name, interpretation)) in enumerate(zip(positions, cards)):
        result += f"{pos}\n"
        result += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        result += f"✨ КАРТА: {name}\n"
        result += f"💫 ГЛУБИННОЕ ЗНАЧЕНИЕ:\n{interpretation['short']}\n\n"
        
        # Для раскладов с >1 картой добавляем интерпретации по сферам
        if len(cards) > 1:
            result += f"❤️‍🔥 В ЛЮБВИ И ОТНОШЕНИЯХ:\n{interpretation['love']}\n\n"
            result += f"💼 В КАРЬЕРЕ И ДЕНЬГАХ:\n{interpretation['career']}\n\n"
    
    # ОДИН ОБЩИЙ СОВЕТ НА ВЕСЬ РАСКЛАД
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    result += "🌟 ГЛУБОКИЙ ПЕРСОНАЛЬНЫЙ СОВЕТ ТАРО 🌟\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Генерируем совет на основе всех карт
    card_names = [card[0] for card in cards]
    advice_parts = []
    
    if "Шут" in card_names or "Маг" in card_names:
        advice_parts.append("✨ Вы находитесь на пороге новых возможностей. Доверяйте своей интуиции и не бойтесь делать первый шаг — вселенная поддерживает ваши начинания. Иногда именно безрассудный прыгок в неизвестность открывает двери к самым удивительным приключениям жизни.")
    
    if "Сила" in card_names or "Отшельник" in card_names:
        advice_parts.append("💫 Сейчас важнее всего внутренняя работа. Уделите время саморефлексии, медитации или ведению дневника. Ответы уже внутри вас — просто прислушайтесь к тишине своего сердца. В уединении рождается мудрость, а в тишине — ясность.")
    
    if "Колесница" in card_names or "Император" in card_names:
        advice_parts.append("🔥 Ваша сила — в дисциплине и целеустремлённости. Составьте чёткий план действий и следуйте ему, несмотря на препятствия. Вы обладаете всем необходимым для достижения целей — верьте в себя и действуйте с уверенностью. Помните: великие империи строятся не за день, а кирпич за кирпичом.")
    
    if "Луна" in card_names or "Башня" in card_names:
        advice_parts.append("🌙 Будьте готовы к неожиданным переменам и проявлению скрытых истин. Не цепляйтесь за старое — иногда разрушение необходимо для нового роста. Доверяйте процессу трансформации, даже если сейчас всё кажется хаотичным. После шторма всегда наступает ясная погода.")
    
    if "Солнце" in card_names or "Звезда" in card_names:
        advice_parts.append("☀️ Вас ждёт период света, радости и гармонии. Радуйтесь мелочам, делитесь своей энергией с близкими. Ваша искренность и открытость притягивают удачу и хороших людей. Не прячьте свой свет — мир нуждается в вашем сиянии. Верьте в лучшее, даже когда обстоятельства кажутся сложными.")
    
    if "Суд" in card_names or "Мир" in card_names:
        advice_parts.append("🎉 Вы завершаете важный цикл в жизни. Подведите итоги, поблагодарите за опыт и смело открывайте новую главу. Вас ждёт гармония, целостность и достижение долгожданной цели. Помните: каждый конец — это новое начало, а каждое завершение — повод для праздника.")
    
    # Если нет специфических советов — общий
    if not advice_parts:
        advice_parts.append("💫 Помните: карты Таро показывают не предопределённое будущее, а возможности и потенциал текущего момента. Выбор всегда остаётся за вами. Доверяйте себе, слушайте своё сердце и действуйте с любовью и осознанностью. Вы сильнее, мудрее и способнее, чем думаете!")
    
    # Объединяем советы в один текст
    result += "\n\n".join(advice_parts)
    result += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    result += "🌙 ВАЖНОЕ НАПОМИНАНИЕ:\n"
    result += "Таро — это инструмент самопознания и рефлексии,\n"
    result += "а не предсказание неизбежного будущего.\n"
    result += "Вы сами создаёте свою реальность каждым своим выбором,\n"
    result += "мышлением и действием. Доверяйте своей мудрости! 💫\n"
    
    return result

# ... (весь файл без изменений, кроме этой функции) ...

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