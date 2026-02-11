import os
import logging
import sqlite3
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from flask import Flask, request
import threading
import re

from database import init_db, add_user, get_balance, decrease_balance, increase_balance, add_referral, mark_subscribed, check_subscribed, get_saved_slots, save_reading, get_saved_reading, delete_saved_reading, create_payment, complete_payment, get_user_data, save_user_data
from tarot_cards import get_random_cards, format_reading, get_single_card

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
NOWPAYMENTS_KEY = os.getenv("NOWPAYMENTS_KEY", "YOUR_API_KEY_HERE")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Состояния для запроса данных
ASKING_NAME, ASKING_BIRTHDATE = range(2)

@app.route('/')
def health_check():
    return "✅ v5.2"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        payment_id = data.get('payment_id')
        status = data.get('payment_status')
        tx_hash = data.get('tx_hash', 'N/A')
        if status == 'confirmed' and payment_id:
            user_id, pack_size = complete_payment(payment_id, tx_hash)
            if user_id:
                def send_notification():
                    application.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ Оплата получена! ✨\n\n💰 На ваш баланс зачислено {pack_size} раскладов.\n🧾 Транзакция: {tx_hash[:10]}...\n\n🎴 Готовы к новому гаданию?"
                    )
                threading.Thread(target=send_notification).start()
                return "OK", 200
        return "Ignored", 200
    except Exception as e:
        print(f"❌ Ошибка вебхука: {e}")
        return "Error", 500

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    add_user(user.id, user.username, user.first_name)
    
    # Обработка реферальной ссылки
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
    
    # Проверяем, есть ли данные пользователя
    user_data = get_user_data(user.id)
    if not user_data or not user_data.get('name') or not user_data.get('birthdate'):
        # Запрашиваем данные
        await update.message.reply_text(
            "✨ Добро пожаловать в мир Таро!\n\n"
            "🔮 Чтобы сделать персонализированный расклад, мне нужны ваши данные:\n"
            "1. Как вас зовут?\n"
            "2. Ваша дата рождения (в формате ДД.ММ.ГГГГ)\n\n"
            "Напишите своё имя:"
        )
        return ASKING_NAME
    
    balance = get_balance(user.id)
    message = f"🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n✨ Ваш баланс: {balance} раскладов"
    
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

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос имени"""
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("❌ Имя должно быть не менее 2 символов. Попробуйте ещё раз:")
        return ASKING_NAME
    
    context.user_data['temp_name'] = name
    await update.message.reply_text(
        f"✨ Приятно познакомиться, {name}!\n\n"
        "Теперь напишите вашу дату рождения в формате ДД.ММ.ГГГГ (например, 15.08.1990):"
    )
    return ASKING_BIRTHDATE

async def ask_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос даты рождения"""
    birthdate = update.message.text.strip()
    # Проверка формата ДД.ММ.ГГГГ
    if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', birthdate):
        await update.message.reply_text(
            "❌ Неверный формат даты. Напишите в формате ДД.ММ.ГГГГ (например, 15.08.1990):"
        )
        return ASKING_BIRTHDATE
    
    # Сохраняем данные пользователя
    user_id = update.effective_user.id
    name = context.user_data.get('temp_name', 'Аноним')
    save_user_data(user_id, name, birthdate)
    
    # Удаляем временные данные
    if 'temp_name' in context.user_data:
        del context.user_data['temp_name']
    
    balance = get_balance(user_id)
    await update.message.reply_text(
        f"✅ Данные сохранены!\n\n"
        f"✨ {name}, ваш баланс: {balance} раскладов\n"
        f"🎴 Готовы к первому раскладу?"
    )
    
    # Показываем меню
    keyboard = [
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
        [InlineKeyboardButton("📺 Подписка (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔮 Выберите действие:",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def create_crypto_invoice(user_id, pack_size, currency="USDT"):
    prices = {1: 100, 3: 285, 7: 630, 13: 1105}
    amount_rub = prices.get(pack_size, 100)
    
    API_URL = "https://api.sandbox.nowpayments.io/v1/invoice"
    
    if not NOWPAYMENTS_KEY or NOWPAYMENTS_KEY == "YOUR_API_KEY_HERE":
        print("❌ ОШИБКА: NOWPAYMENTS_KEY не установлен")
        return None, None, None, None
    
    try:
        headers = {
            "X-API-Key": NOWPAYMENTS_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "price_amount": amount_rub,
            "price_currency": "RUB",
            "pay_currency": currency,
            "order_id": f"taro_{user_id}_{pack_size}",
            "order_description": f"Пакет {pack_size} раскладов Таро",
            "success_url": "https://t.me/cardnotlie_bot"
        }
        
        response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 201:
            invoice = response.json()
            payment_id = invoice['id']
            invoice_url = invoice['invoice_url']
            pay_amount = invoice['pay_amount']
            pay_currency = invoice['pay_currency']
            create_payment(user_id, amount_rub, pack_size, payment_id, pay_currency, pay_amount)
            print(f"✅ Инвойс создан: {payment_id}")
            return payment_id, invoice_url, pay_amount, pay_currency
        else:
            error_msg = response.json().get('message', 'Неизвестная ошибка')
            print(f"❌ Ошибка NOWPayments ({response.status_code}): {error_msg}")
            demo_url = f"https://t.me/cardnotlie_bot?start=pay_demo_{pack_size}"
            return f"demo_{user_id}_{pack_size}", demo_url, amount_rub * 0.012, "USDT"
    except Exception as e:
        print(f"❌ Исключение: {e}")
        demo_url = f"https://t.me/cardnotlie_bot?start=pay_demo_{pack_size}"
        return f"demo_{user_id}_{pack_size}", demo_url, amount_rub * 0.012, "USDT"

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Проверяем, есть ли данные пользователя
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name') or not user_data.get('birthdate'):
        await query.message.reply_text(
            "✨ Для начала гадания мне нужны ваши данные:\n"
            "1. Имя\n"
            "2. Дата рождения (ДД.ММ.ГГГГ)\n\n"
            "Напишите своё имя:"
        )
        return ASKING_NAME
    
    if query.data == 'do_tarot':
        balance = get_balance(user_id)
        
        if balance > 0:
            # Уменьшаем баланс ПЕРЕД созданием расклада
            if not decrease_balance(user_id, 1):
                await query.edit_message_text(text="❌ Ошибка при списании расклада. Попробуйте позже.")
                return
            
            new_balance = get_balance(user_id)  # Получаем новый баланс после списания
            cards = get_random_cards(3)
            reading = format_reading(cards, user_data['name'])
            
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
        else:
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
    
    # ... остальные обработчики кнопок (без изменений, кроме текста помощи) ...
    # Сокращу для краткости — замените только текст помощи ниже
    
    elif query.data == 'help':
        message = (
            "❓ ПОМОЩЬ ❓\n"
            "\n✨ КАК ПОЛЬЗОВАТЬСЯ БОТОМ:\n"
            "1. Нажмите «Сделать расклад».\n"
            "2. Получите мгновенный расклад из 3 карт.\n"
            "3. Нажмите «💾 Сохранить расклад», чтобы не потерять его.\n"
            "\n🗄️ СОХРАНЕНИЕ РАСКЛАДОВ:\n"
            "• У вас есть 3 ячейки для сохранения раскладов.\n"
            "• Расклады НЕ сохраняются автоматически — только по вашему выбору.\n"
            "• Если все ячейки заняты — сначала удалите старый расклад.\n"
            "\n⚖️ БАЛАНС:\n"
            "• При регистрации: 1 бесплатный расклад.\n"
            "• За друга: +1 расклад.\n"
            "• За подписку: +3 расклада.\n"
            "• Покупка пакетов со скидкой до 15%.\n"
            "\n💳 ОПЛАТА:\n"
            "• Криптовалюта — автоматическое зачисление после оплаты ✅\n"
            "• Банковская карта — требуется ручная проверка скриншота ⏳\n"
            "• Подробнее об условиях: /terms"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    # ... остальные elif (без изменений) ...
    
    elif query.data == 'back_to_menu':
        user_data = get_user_data(user_id)
        if not user_data or not user_data.get('name'):
            await query.message.reply_text("Напишите своё имя:")
            return ASKING_NAME
        
        balance = get_balance(user_id)
        message = f"🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n✨ {user_data['name']}, ваш баланс: {balance} раскладов"
        keyboard = [
            [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
            [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
            [InlineKeyboardButton("📺 Подписка (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)

# ... остальные функции (history_command, terms_command, get_referral_count, main, run_flask) без изменений ...

def main():
    global application
    init_db()
    if not TOKEN:
        print("❌ Токен не установлен")
        return
    print("✅ Бот запущен v5.2 (запрос данных, исправленная трата раскладов, чистый интерфейс)")
    
    application = Application.builder().token(TOKEN).build()
    
    # ConversationHandler для запроса данных
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASKING_BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_birthdate)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("terms", terms_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()