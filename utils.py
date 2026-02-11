import sqlite3
import random
import re

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
    
    # ... остальные таблицы (referrals, saved_readings, payments, user_data) ...
    
    conn.commit()
    conn.close()

# ... все функции работы с БД (add_user, get_balance, decrease_balance и т.д.) ...

# === КАРТЫ ТАРО ===

MAJOR_ARCANA = {
    # ... все 22 карты ...
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
    # ... полная функция форматирования ...
    pass

def get_single_card():
    card_name = random.choice(list(MAJOR_ARCANA.keys()))
    return (card_name, MAJOR_ARCANA[card_name])