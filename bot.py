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
    return "✅ v4.2"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
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
    
    balance = get_balance(user.id)
    message = (
        "🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n"
        "✨ Я — ваш личный таролог.\n"
        f"🎯 Ваш баланс: {balance} раскладов"
    )
    
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
    """Обработчик нажатий на кнопки"""
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
            
            # Сохраняем расклад во временное хранилище пользователя
            if 'pending_readings' not in context.user_data:
                context.user_data['pending_readings'] = {}
            context.user_data['pending_readings'][user_id] = (cards, reading)
            
            # Отправляем расклад как НОВОЕ сообщение (не редактируем старое!)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=reading
            )
            
            # Отправляем кнопки как ОТДЕЛЬНОЕ сообщение
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
        # Получаем последний расклад из временного хранилища
        if 'pending_readings' in context.user_data and user_id in context.user_data['pending_readings']:
            cards, reading_text = context.user_data['pending_readings'][user_id]
            
            # Проверяем свободные ячейки
            slots = get_saved_slots(user_id)
            free_slots = [i for i in range(1, 4) if i not in slots]
            
            if free_slots:
                slot = save_reading(user_id, cards, reading_text, free_slots[0])
                if slot:
                    message = f"✅ Расклад сохранён в ячейку #{slot}!\n\nУ вас есть 3 ячейки для хранения раскладов. Посмотреть их можно в меню → «🗄️ Мои расклады»"
                    keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(text=message, reply_markup=reply_markup)
                else:
                    await query.edit_message_text(text="❌ Ошибка сохранения. Попробуйте ещё раз.")
            else:
                # Все ячейки заняты — показываем список для удаления
                message = "⚠️ Все 3 ячейки для сохранения заняты.\n\nСначала удалите один из сохранённых раскладов:"
                keyboard = []
                for slot_num, timestamp in slots.items():
                    keyboard.append([InlineKeyboardButton(f"❌ Ячейка #{slot_num} ({timestamp})", callback_data=f'delete_slot_{slot_num}')])
                keyboard.append([InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text=message, reply_markup=reply_markup)
            
            # Удаляем из временного хранилища
            del context.user_data['pending_readings'][user_id]
        else:
            await query.edit_message_text(text="❌ Нет расклада для сохранения. Сначала сделайте расклад!")
    
    elif query.data.startswith('delete_slot_'):
        slot_num = int(query.data.split('_')[2])
        if delete_saved_reading(user_id, slot_num):
            message = f"✅ Расклад из ячейки #{slot_num} удалён.\nТеперь вы можете сохранить новый расклад!"
        else:
            message = "❌ Ошибка удаления. Попробуйте ещё раз."
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'saved_readings':
        slots = get_saved_slots(user_id)
        if not slots:
            message = "🗄️ МОИ СОХРАНЁННЫЕ РАСКЛАДЫ 🗄️\n\nУ вас пока нет сохранённых раскладов.\nСделайте расклад и нажмите «💾 Сохранить»!"
            keyboard = [[InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')], [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=message, reply_markup=reply_markup)
            return
        
        message = "🗄️ МОИ СОХРАНЁННЫЕ РАСКЛАДЫ 🗄️\n"
        keyboard = []
        for slot_num in sorted(slots.keys()):
            timestamp = slots[slot_num]
            keyboard.append([InlineKeyboardButton(f"📦 Ячейка #{slot_num} ({timestamp})", callback_data=f'view_slot_{slot_num}')])
        keyboard.append([InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data.startswith('view_slot_'):
        slot_num = int(query.data.split('_')[2])
        reading = get_saved_reading(user_id, slot_num)
        if reading:
            cards_str, interpretation, timestamp = reading
            message = f"📦 РАСКЛАД ИЗ ЯЧЕЙКИ #{slot_num}\n📅 {timestamp[:16]}\n\n{interpretation}"
            keyboard = [[InlineKeyboardButton("❌ Удалить этот расклад", callback_data=f'delete_slot_{slot_num}')], [InlineKeyboardButton("⬅️ Назад к списку", callback_data='saved_readings')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="❌ Расклад не найден. Возможно, он был удалён.")
    
    elif query.data == 'balance':
        balance = get_balance(user_id)
        message = (
            f"⚖️ ВАШ ТЕКУЩИЙ БАЛАНС ⚖️\n"
            f"\n🔮 Доступно раскладов: {balance}\n"
            f"\n✨ Как получить больше раскладов:\n"
            f"• Пригласите друга — +1 расклад 🎁\n"
            f"• Подпишитесь на канал — +3 расклада 📺\n"
            f"• Купите пакет раскладов со скидкой 💳"
        )
        keyboard = [
            [InlineKeyboardButton("💳 Купить расклады", callback_data='buy_packs')],
            [InlineKeyboardButton("📺 Подписаться (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'buy_packs':
        message = (
            "💳 ПАКЕТЫ РАСКЛАДОВ 💳\n"
            "\n✨ Выберите пакет со скидкой:\n"
            "\n🎴 1 расклад — 100 ₽\n"
            "   Идеально для разового гадания\n"
            "\n🎴 3 расклада — 285 ₽ (-5%)\n"
            "   Экономия 15 ₽\n"
            "\n🎴 7 раскладов — 630 ₽ (-10%)\n"
            "   Экономия 70 ₽\n"
            "\n🎴 13 раскладов — 1 105 ₽ (-15%)\n"
            "   Экономия 195 ₽"
        )
        keyboard = [
            [InlineKeyboardButton("1 расклад — 100₽", callback_data='buy_1')],
            [InlineKeyboardButton("3 расклада — 285₽ (-5%)", callback_data='buy_3')],
            [InlineKeyboardButton("7 раскладов — 630₽ (-10%)", callback_data='buy_7')],
            [InlineKeyboardButton("13 раскладов — 1 105₽ (-15%)", callback_data='buy_13')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='balance')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data.startswith('buy_'):
        pack_size = int(query.data.split('_')[1])
        prices = {1: 100, 3: 285, 7: 630, 13: 1105}
        price = prices[pack_size]
        discounts = {1: "0%", 3: "5%", 7: "10%", 13: "15%"}
        discount = discounts[pack_size]
        
        message = (
            f"💳 ОПЛАТА ПАКЕТА: {pack_size} раскладов 💳\n"
            f"\n💰 Стоимость: {price} ₽ (скидка {discount})\n"
            f"\n🏦 Реквизиты для оплаты:\n"
            f"▫️ Банк: Райффайзенбанк\n"
            f"▫️ Номер карты: 2200 1234 5678 9012\n"
            f"▫️ Получатель: Сергей Л.\n"
            f"▫️ Сумма: {price} ₽\n"
            f"▫️ Комментарий: taro_{user_id}_{pack_size}\n"
            f"\n✅ ПОСЛЕ ОПЛАТЫ:\n"
            f"1. Сделайте скриншот перевода.\n"
            f"2. Напишите мне с пометкой «ОПЛАТА».\n"
            f"3. Я начислю {pack_size} раскладов на ваш баланс в течение 10 минут! ✨"
        )
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к пакетам", callback_data='buy_packs')],
            [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'subscribe':
        subscribed = check_subscribed(user_id)
        if subscribed:
            message = "✅ Вы уже подписаны на наш канал!\n💫 Бонус +3 расклада уже начислен."
        else:
            message = (
                "📺 ПОДПИСКА НА КАНАЛ 📺\n"
                "\nПодпишитесь на наш эзотерический канал и получите +3 бесплатных расклада!\n"
                "\n✨ Канал: https://t.me/+5q7VJBPU4_QyMDky\n"
                "\nПосле подписки нажмите кнопку ниже:"
            )
        keyboard = [
            [InlineKeyboardButton("📺 Перейти в канал", url="https://t.me/+5q7VJBPU4_QyMDky")],
            [InlineKeyboardButton("✅ Я подписался (+3 расклада)", callback_data='confirm_subscribe')],
            [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'confirm_subscribe':
        subscribed = check_subscribed(user_id)
        if subscribed:
            message = "✅ Вы уже получили бонус за подписку!"
        else:
            mark_subscribed(user_id)
            message = "🎉 Ура! Вы подписались на канал!\n✨ Бонус +3 бесплатных расклада начислен на ваш счёт!"
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'help':
        message = (
            "❓ ПОМОЩЬ ❓\n\n"
            "✨ КАК ПОЛЬЗОВАТЬСЯ БОТОМ:\n"
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
            "• На карту Райффайзенбанк.\n"
            "• После оплаты напишите «ОПЛАТА»."
        )
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'back_to_menu':
        balance = get_balance(user_id)
        message = f"🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n✨ Ваш баланс: {balance} раскладов"
        keyboard = [
            [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
            [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
            [InlineKeyboardButton("📺 Подписка (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /history — показывает сохранённые расклады"""
    user_id = update.effective_user.id
    slots = get_saved_slots(user_id)
    
    if not slots:
        message = "🗄️ МОИ СОХРАНЁННЫЕ РАСКЛАДЫ 🗄️\n\nУ вас пока нет сохранённых раскладов.\nСделайте расклад и нажмите «💾 Сохранить»!"
        keyboard = [[InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text=message, reply_markup=reply_markup)
        return
    
    message = "🗄️ МОИ СОХРАНЁННЫЕ РАСКЛАДЫ 🗄️\n"
    keyboard = []
    for slot_num in sorted(slots.keys()):
        timestamp = slots[slot_num]
        keyboard.append([InlineKeyboardButton(f"📦 Ячейка #{slot_num} ({timestamp})", callback_data=f'view_slot_{slot_num}')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

def main():
    init_db()
    if not TOKEN:
        print("❌ Токен не установлен")
        return
    print("✅ Бот запущен v4.2 (исправлены кнопки после расклада, добавлена /history)")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("history", history_command))  # ВОССТАНОВЛЕНА КОМАНДА /history
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()