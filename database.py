import sqlite3

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    # Таблица пользователей (баланс раскладов)
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
    
    # Таблица СОХРАНЁННЫХ раскладов (НОВОЕ! — 3 ячейки на пользователя)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS saved_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            slot INTEGER,  -- ячейка 1, 2 или 3
            cards TEXT,
            interpretation TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, slot)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована (система ячеек для сохранения)")

def add_user(user_id, username, first_name):
    """Добавить пользователя в базу"""
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
    return cursor.rowcount > 0

def increase_balance(user_id, amount=1):
    """Увеличить баланс на указанное количество"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def add_referral(referrer_id, referred_id):
    """Добавить реферала (+1 к балансу)"""
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
    """Отметить подписку (+3 к балансу)"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('UPDATE users SET subscribed = 1, balance = balance + 3 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True

def check_subscribed(user_id):
    """Проверить подписку"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT subscribed FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else 0

# ===== НОВЫЕ ФУНКЦИИ ДЛЯ СИСТЕМЫ ЯЧЕЕК =====

def get_saved_slots(user_id):
    """Получить список занятых ячеек пользователя (1, 2, 3)"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT slot, timestamp FROM saved_readings WHERE user_id = ? ORDER BY slot ASC', (user_id,))
    results = cursor.fetchall()
    conn.close()
    
    # Возвращаем словарь: {слот: дата}
    return {row[0]: row[1][:16] for row in results}

def save_reading(user_id, cards, interpretation, slot=None):
    """
    Сохранить расклад в ячейку
    
    Args:
        user_id: ID пользователя
        cards: список карт [(название, интерпретация), ...]
        interpretation: полный текст расклада
        slot: ячейка (1-3), если None — найти первую свободную
    
    Returns:
        номер ячейки или None если нет свободных мест
    """
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    # Если слот не указан — найти первую свободную ячейку
    if slot is None:
        occupied = get_saved_slots(user_id).keys()
        for i in range(1, 4):
            if i not in occupied:
                slot = i
                break
    
    # Если нет свободных ячеек — вернуть None
    if slot is None or slot not in [1, 2, 3]:
        conn.close()
        return None
    
    # Сохраняем расклад (заменяем существующий в этой ячейке)
    cards_str = ','.join([card[0] for card in cards])
    
    cursor.execute('''
        INSERT OR REPLACE INTO saved_readings (user_id, slot, cards, interpretation)
        VALUES (?, ?, ?, ?)
    ''', (user_id, slot, cards_str, interpretation))
    
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
    
    return result  # (cards_str, interpretation, timestamp) или None

def delete_saved_reading(user_id, slot):
    """Удалить расклад из ячейки"""
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM saved_readings WHERE user_id = ? AND slot = ?', (user_id, slot))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0