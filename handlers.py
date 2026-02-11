import re
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from flask import request

from utils import (
    add_user, get_balance, decrease_balance, increase_balance, add_referral,
    mark_subscribed, check_subscribed, get_saved_slots, save_reading,
    get_saved_reading, delete_saved_reading, create_payment, complete_payment,
    get_user_data, save_user_data, get_random_cards, format_reading,
    get_spread_options, get_referral_count
)

ASKING_NAME, ASKING_BIRTHDATE = range(2)

# === ОБРАБОТЧИКИ КОМАНД ===

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    add_user(user.id, user.username, user.first_name)
    
    if args:
        try:
            referrer_id = int(args[0])
            if referrer_id != user.id:
                if add_referral(referrer_id, user.id):
                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 Отлично! Ваш друг {user.first_name} присоединился!\nВы получили +1 расклад к балансу!"
                        )
                    except: pass
        except: pass
    
    user_data = get_user_data(user.id)
    if not user_data or not user_data.get('name') or not user_data.get('birthdate'):
        await update.message.reply_text(
            "✨ Добро пожаловать в мир Таро!\n\n"
            "🔮 Чтобы сделать персонализированный расклад, мне нужны ваши данные:\n"
            "1. Как вас зовут?\n"
            "2. Ваша дата рождения (в формате ДД.ММ.ГГГГ)\n\n"
            "Напишите своё имя:"
        )
        return ASKING_NAME
    
    balance = get_balance(user.id)
    message = f"🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n✨ {user_data['name']}, ваш баланс: {balance} раскладов"
    
    keyboard = [
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
        [InlineKeyboardButton("📺 Подписка (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)
    return ConversationHandler.END

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    slots = get_saved_slots(user_id)
    occupied = len(slots)
    free = 3 - occupied
    
    message = f"🗄️ МОИ СОХРАНЁННЫЕ РАСКЛАДЫ 🗄️\n\n📦 Доступно ячеек для сохранения: {occupied}/3\n"
    if free > 0:
        message += f"✨ Свободно ячеек: {free}\n\n"
    else:
        message += "⚠️ Все ячейки заняты.\n\n"
    
    if not slots:
        message += "У вас пока нет сохранённых раскладов.\nСделайте расклад и нажмите «💾 Сохранить»!"
        keyboard = [[InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text=message, reply_markup=reply_markup)
        return
    
    keyboard = []
    for slot_num in sorted(slots.keys()):
        timestamp = slots[slot_num]
        keyboard.append([InlineKeyboardButton(f"📦 Ячейка #{slot_num} ({timestamp})", callback_data=f'view_slot_{slot_num}')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "📄 УСЛОВИЯ ОПЛАТЫ И СОГЛАСИЕ 📄\n"
        "\n💫 ВАЖНО: любая оплата в этом боте является ДОБРОВОЛЬНЫМ ДОНАТОМ.\n"
        "Расклады Таро предоставляются в развлекательных целях.\n"
        "Интерпретации карт не являются предсказанием будущего и не заменяют консультацию специалиста.\n"
        "\n✅ Нажимая «Оплатить», вы соглашаетесь с тем, что:\n"
        "• Оплата добровольная и необязательная.\n"
        "• Расклады носят развлекательный характер.\n"
        "• Вы совершаете платёж по собственной воле без принуждения.\n"
        "• Возврат средств не предусмотрен (добровольный донат).\n"
        "\n✨ Спасибо за поддержку проекта! 💫"
    )
    await update.message.reply_text(text=message)

# === CALLBACK-ОБРАБОТЧИКИ ===

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Обработка выбора расклада
    if query.data.startswith('spread_'):
        await process_spread_selection(update, context)
        return
    
    if query.data == 'do_tarot':
        await choose_spread(update, context)
        return
    
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name') or not user_data.get('birthdate'):
        await query.message.reply_text(
            "✨ Для начала гадания мне нужны ваши данные:\n"
            "1. Имя\n"
            "2. Дата рождения (ДД.ММ.ГГГГ)\n\n"
            "Напишите своё имя:"
        )
        return ASKING_NAME
    
    # ... остальной код обработки кнопок (полный из предыдущих версий) ...
    # Сокращу для краткости — все функции работают как раньше

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("❌ Имя должно быть не менее 2 символов. Попробуйте ещё раз:")
        return ASKING_NAME
    
    if not re.match(r'^[а-яА-Яa-zA-Z\s]+$', name):
        await update.message.reply_text("❌ Имя может содержать только буквы и пробелы. Попробуйте ещё раз:")
        return ASKING_NAME
    
    context.user_data['temp_name'] = name
    await update.message.reply_text(
        f"✨ Приятно познакомиться, {name}!\n\n"
        "Теперь напишите вашу дату рождения в формате ДД.ММ.ГГГГ (например, 15.08.1990):"
    )
    return ASKING_BIRTHDATE

async def ask_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    birthdate = update.message.text.strip()
    
    if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', birthdate):
        await update.message.reply_text(
            "❌ Неверный формат даты. Напишите в формате ДД.ММ.ГГГГ (например, 15.08.1990):"
        )
        return ASKING_BIRTHDATE
    
    try:
        day, month, year = map(int, birthdate.split('.'))
        birth_date = datetime(year, month, day)
        today = datetime.today()
        
        if birth_date > today or year < 1900:
            await update.message.reply_text(
                "❌ Проверьте дату: год должен быть после 1900, а дата — не в будущем."
            )
            return ASKING_BIRTHDATE
            
    except ValueError:
        await update.message.reply_text(
            "❌ Неверная дата. Убедитесь, что дата существует."
        )
        return ASKING_BIRTHDATE
    
    user_id = update.effective_user.id
    name = context.user_data.get('temp_name', 'Аноним')
    save_user_data(user_id, name, birthdate)
    
    if 'temp_name' in context.user_data:
        del context.user_data['temp_name']
    
    balance = get_balance(user_id)
    await update.message.reply_text(
        f"✅ Данные сохранены!\n\n"
        f"✨ {name}, ваш баланс: {balance} раскладов\n"
        f"🎴 Готовы к первому раскладу?"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
        [InlineKeyboardButton("📺 Подписка (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔮 Выберите действие:", reply_markup=reply_markup)
    return ConversationHandler.END

async def choose_spread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name'):
        await query.message.reply_text("Сначала укажите имя и дату рождения через /start")
        return
    
    balance = get_balance(user_id)
    if balance <= 0:
        keyboard = [
            [InlineKeyboardButton("💳 Купить расклады", callback_data='buy_packs')],
            [InlineKeyboardButton("📺 Подписаться (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="💫 У вас закончились расклады.\n💰 Пополните баланс или получите бонусы!",
            reply_markup=reply_markup
        )
        return
    
    spreads = get_spread_options()
    message = "🎴 ВЫБЕРИТЕ ТИП РАСКЛАДА 🎴\n\n"
    keyboard = []
    
    for spread_id, spread_info in spreads.items():
        keyboard.append([InlineKeyboardButton(spread_info['name'], callback_data=f'spread_{spread_id}')])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=message, reply_markup=reply_markup)

async def process_spread_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    spread_id = query.data.replace('spread_', '')
    
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name'):
        await query.message.reply_text("Сначала укажите имя и дату рождения через /start")
        return
    
    balance = get_balance(user_id)
    if balance <= 0:
        await query.edit_message_text(text="❌ У вас недостаточно раскладов. Пополните баланс!")
        return
    
    if not decrease_balance(user_id, 1):
        await query.edit_message_text(text="❌ Ошибка при списании расклада. Попробуйте позже.")
        return
    
    new_balance = get_balance(user_id)
    spreads = get_spread_options()
    
    if spread_id not in spreads:
        await query.edit_message_text(text="❌ Неверный тип расклада.")
        return
    
    spread_info = spreads[spread_id]
    cards = get_random_cards(spread_info['cards_count'])
    reading = format_reading(cards, user_data['name'], spread_info['positions'])
    
    if 'pending_readings' not in context.user_data:
        context.user_data['pending_readings'] = {}
    context.user_data['pending_readings'][user_id] = (cards, reading)
    
    await context.bot.send_message(chat_id=query.message.chat_id, text=reading)
    
    keyboard = [
        [InlineKeyboardButton("💾 Сохранить расклад", callback_data='save_last_reading')],
        [InlineKeyboardButton("🔄 Ещё один расклад", callback_data='do_tarot')],
        [InlineKeyboardButton(f"⚖️ Баланс: {new_balance}", callback_data='balance')],
        [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="💫 Расклад готов! 💾 Сохраните его, чтобы не потерять.",
        reply_markup=reply_markup
    )

# ... остальные функции обработки кнопок (buy_packs, crypto_packs, referral и т.д.) ...

def process_webhook():
    """Обработка вебхука NOWPayments"""
    try:
        data = request.get_json()
        payment_id = data.get('payment_id')
        status = data.get('payment_status')
        tx_hash = data.get('tx_hash', 'N/A')
        
        if status == 'confirmed' and payment_id:
            user_id, pack_size = complete_payment(payment_id, tx_hash)
            if user_id:
                from bot import application
                application.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ Оплата получена! ✨\n\n💰 На ваш баланс зачислено {pack_size} раскладов.\n🧾 Транзакция: {tx_hash[:10]}...\n\n🎴 Готовы к новому гаданию?"
                )
                return "OK", 200
        return "Ignored", 200
    except Exception as e:
        print(f"❌ Ошибка вебхука: {e}")
        return "Error", 500