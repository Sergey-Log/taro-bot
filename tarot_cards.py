import random

MAJOR_ARCANA = {
    # ... (все 22 карты как в предыдущей версии) ...
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
        positions = ["🎴 КАРТА"] * len(cards)
    
    result = f"🔮 ПЕРСОНАЛИЗИРОВАННЫЙ РАСКЛАД ДЛЯ {user_name.upper()} 🔮\n"
    result += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for pos, (name, interpretation) in zip(positions, cards):
        result += f"{pos}\n"
        result += f"━━━━━━━━━━━━━━━━━━━━\n"
        result += f"✨ Карта: {name}\n"
        result += f"💫 Значение: {interpretation['short']}\n\n"
        
        # Добавляем интерпретации только для много-картных раскладов
        if len(cards) > 1:
            result += f"❤️‍🔥 В любви: {interpretation['love']}\n"
            result += f"💼 В карьере: {interpretation['career']}\n\n"
    
    # ОДИН ОБЩИЙ СОВЕТ НА ВЕСЬ РАСКЛАД
    result += "━━━━━━━━━━━━━━━━━━━━\n"
    result += "🌟 ПЕРСОНАЛЬНЫЙ СОВЕТ ТАРО 🌟\n"
    result += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Генерируем совет на основе всех карт
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

def get_single_card():
    """Получить одну случайную карту (для карты дня)"""
    card_name = random.choice(list(MAJOR_ARCANA.keys()))
    return (card_name, MAJOR_ARCANA[card_name])