import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask
import threading

from database import init_db, add_user, check_free_used, mark_free_used, add_referral, get_referral_count
from tarot_cards import get_random_cards, format_reading

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def health_check():
    return "? Бот работает! Таро бот @cardnotlie_bot v2.1"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    add_user(user.id, user.username, user.first_name)
    
    if args:
        try:
            referrer_id = int(args[0])
            if referrer_id != user.id:
                if add_referral(referrer_id, user.id):
                    try:
                        await context.bot.send_message(chat_id=referrer_id, text=f"?? Отлично! Ваш друг {user.first_name} присоединился!\nВы получили +1 к реферальному счёту!")
                    except: pass
        except: pass
    
    referral_count = get_referral_count(user.id)
    message = f"?? ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! ??\n\n? Я — ваш личный таролог.\n\n?? ЧТО Я МОГУ:\n• Расклады на любые вопросы\n• Анализ ситуации\n• Прогнозы на будущее\n\n?? ПЕРВЫЙ РАСКЛАД — БЕСПЛАТНО!\n?? Ваш реферальный баланс: {referral_count} бесплатных раскладов\n\n?? Чтобы начать, нажмите кнопку ниже!"
    
    keyboard = [
        [InlineKeyboardButton("?? Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton("?? Реферальная программа", callback_data='referral')],
        [InlineKeyboardButton("?? Назад", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'do_tarot':
        free_used = check_free_used(user_id)
        if not free_used:
            cards = get_random_cards(3)
            reading = format_reading(cards)
            mark_free_used(user_id)
            keyboard = [[InlineKeyboardButton("?? Ещё один расклад", callback_data='do_tarot')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=reading, reply_markup=reply_markup)
        else:
            keyboard = [
                [InlineKeyboardButton("?? Оплатить 100?", callback_data='pay_button')],
                [InlineKeyboardButton("?? Пригласить друга", callback_data='referral')],
                [InlineKeyboardButton("?? Назад в меню", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text="?? У вас закончились бесплатные расклады.\n\n?? Стоимость следующего расклада: 100 ?", reply_markup=reply_markup)
    
    elif query.data == 'back_to_menu':
        await start(update, context)

def main():
    init_db()
    if not TOKEN:
        print("? Токен не установлен")
        return
    print("? Бот запущен v2.1 (без ошибок форматирования)")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()