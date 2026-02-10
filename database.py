import sqlite3

def init_db():
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, free_used BOOLEAN DEFAULT 0, referral_count INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS referrals (id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER, referred_id INTEGER)')
    conn.commit()
    conn.close()
    print("? ���� ������ ����������������")

def add_user(user_id, username, first_name):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)', (user_id, username, first_name))
    conn.commit()
    conn.close()

def check_free_used(user_id):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT free_used FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def mark_free_used(user_id):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET free_used = 1 WHERE user_id = ?', (user_id,))
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
    cursor.execute('UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?', (referrer_id,))
    conn.commit()
    conn.close()
    return True

def get_referral_count(user_id):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT referral_count FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0
