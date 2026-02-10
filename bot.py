import os
import logging
print('? НОВАЯ ВЕРСИЯ v2.0 ЗАГРУЖЕНА')
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask
import threading

from database import init_db, add_user, check_free_used, mark_free_used, add_referral, get_referral_count
from tarot_cards import get_random_cards, format_reading, get_single_card

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def health_check():
    return "? Бот работает! Таро бот @cardnotlie_bot v2.0"

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
                        await context.bot.send_message(chat_id=referrer_id, text=f"?? Отлично! Ваш друг {user.first_name} присоединился!
Вы получили +1 к реферальному счёту!")
                    except: pass
        except: pass
    
    referral_count = get_referral_count(user.id)
    message = "?? *ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО!* ??
? Я — ваш личный таролог.

*?? ЧТО Я МОГУ:*
• Расклады на любые вопросы
• Анализ ситуации
• Прогнозы

*?? ПЕРВЫЙ РАСКЛАД — БЕСПЛАТНО!*
?? Реферальный баланс: *{referral_count}* раскладов

Нажмите кнопку ниже!".format(referral_count=referral_count)
    
    keyboard = [[InlineKeyboardButton("?? Сделать расклад", callback_data='do_tarot')], [InlineKeyboardButton("?? Рефералы", callback_data='referral')], [InlineKeyboardButton("? Помощь", callback_data='help')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, parse_mode='MarkdownV2', reply_markup=reply_markup)

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
            keyboard = [[InlineKeyboardButton("?? Ещё один", callback_data='do_tarot')]]
            await query.edit_message_text(text=reading, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')
        else:
            keyboard = [[InlineKeyboardButton("?? 100?", callback_data='pay_button')], [InlineKeyboardButton("?? Друг", callback_data='referral')], [InlineKeyboardButton("?? Назад", callback_data='back_to_menu')]]
            await query.edit_message_text(text="?? Расклады закончились.
?? Следующий: 100 ?", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == 'back_to_menu':
        referral_count = get_referral_count(user_id)
        message = "?? *ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО!* ??
? Ваш таролог.

*?? ПЕРВЫЙ РАСКЛАД — БЕСПЛАТНО!*
?? Баланс: *{referral_count}* раскладов".format(referral_count=referral_count)
        keyboard = [[InlineKeyboardButton("?? Сделать расклад", callback_data='do_tarot')], [InlineKeyboardButton("?? Рефералы", callback_data='referral')], [InlineKeyboardButton("? Помощь", callback_data='help')]]
        await query.edit_message_text(text=message, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))

def main():
    init_db()
    if not TOKEN:
        print("? Токен не установлен")
        return
    print("? Бот запущен v2.0")
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
