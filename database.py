import sqlite3

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            free_used BOOLEAN DEFAULT 0,
            referral_count INTEGER DEFAULT 0,
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
    
    # Таблица раскладов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT,
            cards TEXT,
            is_paid BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def add_user(user_id, username, first_name):
    """Добавить пользователя в базу"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
    ''', (user_id, username, first_name))
    
    conn.commit()
    conn.close()

def check_free_used(user_id):
    """Проверить, использовал ли пользователь бесплатный расклад"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT free_used FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else 0

def mark_free_used(user_id):
    """Отметить, что пользователь использовал бесплатный расклад"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('UPDATE users SET free_used = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def add_referral(referrer_id, referred_id):
    """Добавить реферала"""
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
    
    # Увеличиваем счётчик рефереру
    cursor.execute('UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?', (referrer_id,))
    
    conn.commit()
    conn.close()
    return True

def get_referral_count(user_id):
    """Получить количество рефералов пользователя"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT referral_count FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else 0

def get_user(user_id):
    """Получить данные пользователя"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result