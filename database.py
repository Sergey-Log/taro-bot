import sqlite3

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    # Таблица пользователей (упрощённая: один счётчик баланса)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            balance INTEGER DEFAULT 1,  -- 1 бесплатный расклад при регистрации
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
    
    # Таблица истории раскладов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            cards TEXT,
            interpretation TEXT,
            positions TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована (баланс вместо free_used)")

def add_user(user_id, username, first_name):
    """Добавить пользователя в базу (с балансом = 1)"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, balance)
        VALUES (?, ?, ?, 1)
    ''', (user_id, username, first_name))
    
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
    return cursor.rowcount > 0  # True если баланс был уменьшен

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
    
    # Проверяем, не был ли пользователь уже приглашён
    cursor.execute('SELECT id FROM referrals WHERE referred_id = ?', (referred_id,))
    if cursor.fetchone():
        conn.close()
        return False
    
    # Добавляем реферала
    cursor.execute('''
        INSERT INTO referrals (referrer_id, referred_id)
        VALUES (?, ?)
    ''', (referrer_id, referred_id))
    
    # Увеличиваем баланс рефереру
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

def add_reading(user_id, cards, interpretation, positions=None):
    """Добавить расклад в историю"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cards_str = ','.join([card[0] for card in cards])
    positions_str = ','.join(positions) if positions else 'Прошлое,Настоящее,Будущее'
    
    cursor.execute('''
        INSERT INTO readings (user_id, cards, interpretation, positions)
        VALUES (?, ?, ?, ?)
    ''', (user_id, cards_str, interpretation, positions_str))
    
    conn.commit()
    conn.close()

def get_reading_dates(user_id, limit=10):
    """Получить уникальные даты раскладов пользователя"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT DATE(timestamp) as date_str, COUNT(*) as count
        FROM readings 
        WHERE user_id = ?
        GROUP BY DATE(timestamp)
        ORDER BY date_str DESC
        LIMIT ?
    ''', (user_id, limit))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_readings_by_date(user_id, date_str):
    """Получить все расклады за указанную дату"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT cards, interpretation, positions, timestamp 
        FROM readings 
        WHERE user_id = ? AND DATE(timestamp) = ?
        ORDER BY timestamp DESC
    ''', (user_id, date_str))
    
    results = cursor.fetchall()
    conn.close()
    return results