import os
import logging
import sqlite3
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask
import threading

from database import init_db, add_user, get_balance, decrease_balance, increase_balance, add_referral, mark_subscribed, check_subscribed, get_saved_slots, save_reading, get_saved_reading, delete_saved_reading
from tarot_cards import get_random_cards, format_reading, get_single_card

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ v4.4"

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
                        await context.bot.send_message(chat_id=referrer_id, text=f"🎉 Отлично! Ваш друг {user.first_name} присоединился!\nВы получили +1 расклад к балансу!")
                    except: pass
        except: pass
    
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
    
    if update.message:
        await update.message.reply_text(text=message, reply_markup=reply_markup)
    else:
        query = update.callback_query
        if query:
            await query.edit_message_text(text=message, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'do_tarot':
        balance = get_balance(user_id)
        if balance > 0:
            decrease_balance(user_id, 1)
            cards = get_random_cards(3)
            reading = format_reading(cards)
            new_balance = get_balance(user_id)
            
            # ИСПРАВЛЕНО: правильная работа с user_data
            if 'pending_readings' not in context.user_
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
    
    elif query.data == 'save_last_reading':
        if 'pending_readings' in context.user_data and user_id in context.user_data['pending_readings']:
            cards, reading_text = context.user_data['pending_readings'][user_id]
            slots = get_saved_slots(user_id)
            free_slots = [i for i in range(1, 4) if i not in slots]
            
            if free_slots:
                slot = save_reading(user_id, cards, reading_text, free_slots[0])
                message = f"✅ Расклад сохранён в ячейку #{slot}!"
                keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text=message, reply_markup=reply_markup)
                del context.user_data['pending_readings'][user_id]
            else:
                message = "⚠️ Все 3 ячейки заняты. Сначала удалите старый расклад:"
                keyboard = [[InlineKeyboardButton(f"❌ Ячейка #{s}", callback_data=f'delete_slot_{s}') for s in slots.keys()], [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text=message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="❌ Нет расклада для сохранения.")
    
    elif query.data.startswith('delete_slot_'):
        slot_num = int(query.data.split('_')[2])
        delete_saved_reading(user_id, slot_num)
        await query.edit_message_text(text=f"✅ Расклад из ячейки #{slot_num} удалён.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]))
    
    elif query.data == 'saved_readings':
        slots = get_saved_slots(user_id)
        occupied = len(slots)
        message = f"🗄️ МОИ СОХРАНЁННЫЕ РАСКЛАДЫ 🗄️\n📦 Доступно ячеек: {occupied}/3\n\n"
        if not slots:
            message += "У вас пока нет сохранённых раскладов."
            keyboard = [[InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')], [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        else:
            keyboard = [[InlineKeyboardButton(f"📦 Ячейка #{s} ({t[:16]})", callback_data=f'view_slot_{s}') for s, t in slots.items()], [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data.startswith('view_slot_'):
        slot_num = int(query.data.split('_')[2])
        reading = get_saved_reading(user_id, slot_num)
        if reading:
            _, interpretation, timestamp = reading
            message = f"📦 РАСКЛАД ИЗ ЯЧЕЙКИ #{slot_num}\n📅 {timestamp[:16]}\n\n{interpretation}"
            keyboard = [[InlineKeyboardButton("❌ Удалить", callback_data=f'delete_slot_{slot_num}')], [InlineKeyboardButton("⬅️ Назад", callback_data='saved_readings')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="❌ Расклад не найден.")
    
    elif query.data == 'balance':
        balance = get_balance(user_id)
        message = f"⚖️ ВАШ БАЛАНС ⚖️\n🔮 Раскладов: {balance}"
        keyboard = [
            [InlineKeyboardButton("💳 Купить расклады", callback_data='buy_packs')],
            [InlineKeyboardButton("💫 Пригласить друга", callback_data='referral')],
            [InlineKeyboardButton("📺 Подписаться (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'referral':
        ref_link = f"https://t.me/cardnotlie_bot?start={user_id}"
        referral_count = get_referral_count(user_id)
        message = f"🎁 РЕФЕРАЛЬНАЯ ПРОГРАММА 🎁\nВаша ссылка:\n{ref_link}\n\nПриглашено: {referral_count} друзей"
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'buy_packs':
        message = "💳 ПАКЕТЫ РАСКЛАДОВ 💳\n\n🎴 1 расклад — 100 ₽\n🎴 3 расклада — 285 ₽ (-5%)\n🎴 7 раскладов — 630 ₽ (-10%)\n🎴 13 раскладов — 1 105 ₽ (-15%)"
        keyboard = [
            [InlineKeyboardButton("1 — 100₽", callback_data='buy_1')],
            [InlineKeyboardButton("3 — 285₽", callback_data='buy_3')],
            [InlineKeyboardButton("7 — 630₽", callback_data='buy_7')],
            [InlineKeyboardButton("13 — 1105₽", callback_data='buy_13')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='balance')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data.startswith('buy_'):
        pack_size = int(query.data.split('_')[1])
        prices = {1: 100, 3: 285, 7: 630, 13: 1105}
        price = prices[pack_size]
        message = f"💳 ОПЛАТА: {pack_size} раскладов за {price} ₽\n\n▫️ Банк: Райффайзенбанк\n▫️ Номер карты: \n▫️ Получатель: Сергей Л.\n▫️ Сумма: {price} ₽\n\n✅ После оплаты напишите @jobphone_admin с пометкой «ОПЛАТА»."
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='buy_packs')], [InlineKeyboardButton("📄 Условия", callback_data='terms')], [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'terms':
        message = "📄 УСЛОВИЯ ОПЛАТЫ 📄\n\n💫 Любая оплата является ДОБРОВОЛЬНЫМ ДОНАТОМ.\nРасклады носят развлекательный характер.\nВозврат средств не предусмотрен.\nПодробнее: /terms"
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='buy_packs')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'subscribe':
        if check_subscribed(user_id):
            message = "✅ Вы уже подписаны! Бонус +3 расклада начислен."
        else:
            message = "📺 ПОДПИСКА НА КАНАЛ 📺\n\nПодпишитесь и получите +3 расклада:\nhttps://t.me/+5q7VJBPU4_QyMDky"
        keyboard = [
            [InlineKeyboardButton("📺 Перейти в канал", url="https://t.me/+5q7VJBPU4_QyMDky")],
            [InlineKeyboardButton("✅ Я подписался", callback_data='confirm_subscribe')],
            [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'confirm_subscribe':
        mark_subscribed(user_id)
        await query.edit_message_text(text="🎉 Бонус +3 расклада начислен!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]))
    
    elif query.data == 'help':
        message = "❓ ПОМОЩЬ ❓\n\n• Сделайте расклад → сохраните его в ячейку (3 шт)\n• Баланс пополняется через друзей, подписку или покупку\n• Оплата — добровольный донат: @jobphone_admin\n• Условия: /terms"
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'back_to_menu':
        await start(update, context)

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    slots = get_saved_slots(user_id)
    message = f"🗄️ СОХРАНЁННЫЕ РАСКЛАДЫ ({len(slots)}/3):\n\n"
    if not slots:
        message += "Пусто. Сделайте расклад и сохраните его!"
        keyboard = [[InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')]]
    else:
        keyboard = [[InlineKeyboardButton(f"📦 Ячейка #{s}", callback_data=f'view_slot_{s}') for s in slots.keys()]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(text="📄 УСЛОВИЯ ОПЛАТЫ 📄\n\n💫 Любая оплата является ДОБРОВОЛЬНЫМ ДОНАТОМ.\nРасклады Таро предоставляются в развлекательных целях.\nИнтерпретации не являются предсказанием будущего.\nВозврат средств не предусмотрен.\nСовершая платёж, вы соглашаетесь с условиями.")

def get_referral_count(user_id):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def main():
    init_db()
    if not TOKEN:
        print("❌ Токен не установлен")
        return
    print("✅ Бот запущен v4.4 (исправлено: синтаксическая ошибка в user_data)")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
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