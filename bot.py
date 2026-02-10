import os
import logging
import sqlite3
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask
import threading

from database import init_db, add_user, get_balance, decrease_balance, increase_balance, add_referral, mark_subscribed, check_subscribed, add_reading, get_reading_dates, get_readings_by_date
from tarot_cards import get_random_cards, format_reading, get_single_card

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ v4.0"

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
        "🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n\n"
        "✨ Я — ваш личный таролог, готовый раскрыть тайны будущего.\n"
        "💫 ЧТО Я МОГУ:\n"
        "• Мгновенные расклады на любые вопросы 💫\n"
        "• Глубокий анализ в любви и карьере ❤️‍🔥💼\n"
        "• Персональные советы от карт 🌟\n"
        "• История всех ваших раскладов 📚\n"
        f"\n🎯 Ваш текущий баланс: {balance} раскладов"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
        [InlineKeyboardButton("📺 Подписка (+3 расклада)", callback_data='subscribe')],
        [InlineKeyboardButton("📚 История раскладов", callback_data='history_dates')],
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
            # Уменьшаем баланс
            decrease_balance(user_id, 1)
            
            # Делаем расклад
            cards = get_random_cards(3)
            reading = format_reading(cards)
            add_reading(user_id, cards, reading)
            
            # Отправляем расклад КАК НОВОЕ СООБЩЕНИЕ
            await query.message.reply_text(text=reading)
            
            # Обновляем баланс и отправляем кнопки
            new_balance = get_balance(user_id)
            keyboard = [
                [InlineKeyboardButton("🔄 Ещё один расклад", callback_data='do_tarot')],
                [InlineKeyboardButton(f"⚖️ Баланс: {new_balance}", callback_data='balance')],
                [InlineKeyboardButton("📚 История раскладов", callback_data='history_dates')],
                [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text=f"💫 Баланс обновлён: {new_balance} раскладов",
                reply_markup=reply_markup
            )
        else:
            # Нет раскладов — показываем баланс с пакетами
            keyboard = [
                [InlineKeyboardButton("💳 Купить расклады", callback_data='buy_packs')],
                [InlineKeyboardButton("📚 История раскладов", callback_data='history_dates')],
                [InlineKeyboardButton("📺 Подписаться (+3)", callback_data='subscribe')],
                [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text="💫 У вас закончились расклады.\n💰 Пополните баланс или получите бонусы!",
                reply_markup=reply_markup
            )
    
    elif query.data == 'balance':
        balance = get_balance(user_id)
        message = (
            f"⚖️ ВАШ ТЕКУЩИЙ БАЛАНС ⚖️\n"
            f"\n🔮 Доступно раскладов: {balance}\n"
            f"💫 Каждый расклад — это 3 карты Таро с полной интерпретацией.\n"
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
            "\n🎴 1 расклад — 100 ₽ (без скидки)\n"
            "   Идеально для разового гадания\n"
            "\n🎴 3 расклада — 285 ₽ (-5%)\n"
            "   Экономия 15 ₽\n"
            "\n🎴 7 раскладов — 630 ₽ (-10%)\n"
            "   Экономия 70 ₽\n"
            "\n🎴 13 раскладов — 1 105 ₽ (-15%)\n"
            "   Экономия 195 ₽\n"
            "\nВыберите пакет для покупки:"
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
            message = "✅ Вы уже подписаны на наш канал!\n💫 Бонус +3 расклада уже начислен на ваш счёт."
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
            message = "🎉 Ура! Вы подписались на канал!\n✨ Бонус +3 бесплатных расклада начислен на ваш счёт.\n💫 Теперь у вас есть дополнительные возможности для гадания!"
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'history_dates':
        dates = get_reading_dates(user_id, limit=10)
        if not dates:
            message = "📚 ИСТОРИЯ РАСКЛАДОВ 📚\n\nУ вас пока нет сохранённых раскладов.\nСделайте первый расклад прямо сейчас!"
            keyboard = [[InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')], [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=message, reply_markup=reply_markup)
            return
        
        message = "📚 ВЫБЕРИТЕ ДАТУ РАСКЛАДА 📚\n"
        keyboard = []
        for date_str, count in dates:
            keyboard.append([InlineKeyboardButton(f"📅 {date_str} ({count} раскладов)", callback_data=f'history_date_{date_str}')])
        keyboard.append([InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data.startswith('history_date_'):
        date_str = query.data.split('_', 2)[2]
        readings = get_readings_by_date(user_id, date_str)
        
        if not readings:
            message = f"❌ Расклады за {date_str} не найдены."
        else:
            message = f"📚 РАСКЛАДЫ ЗА {date_str} 📚\n\n"
            for i, (cards, interpretation, positions, timestamp) in enumerate(readings, 1):
                message += f"Расклад #{i} | ⏰ {timestamp[11:16]}\n"
                message += f"━━━━━━━━━━━━━━━━━━━━\n"
                message += interpretation + "\n\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ Выбрать другую дату", callback_data='history_dates')], [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'help':
        message = (
            "❓ ПОМОЩЬ ❓\n\n"
            "✨ КАК ПОЛЬЗОВАТЬСЯ БОТОМ:\n"
            "1. Нажмите /start для начала работы.\n"
            "2. Нажмите «Сделать расклад».\n"
            "3. Получите мгновенный расклад из 3 карт Таро.\n"
            "4. Расклад сохраняется в вашу историю.\n"
            "\n⚖️ БАЛАНС РАСКЛАДОВ:\n"
            "• При регистрации вы получаете 1 бесплатный расклад.\n"
            "• За каждого приглашённого друга — +1 расклад.\n"
            "• За подписку на канал — +3 расклада.\n"
            "• Расклады можно купить со скидкой до 15%.\n"
            "\n📺 ПОДПИСКА НА КАНАЛ:\n"
            "• Канал: https://t.me/+5q7VJBPU4_QyMDky\n"
            "• Бонус: +3 бесплатных расклада.\n"
            "\n💳 ОПЛАТА:\n"
            "• Оплата на карту Райффайзенбанк.\n"
            "• После оплаты напишите «ОПЛАТА» с подтверждением.\n"
            "• Расклады начисляются вручную в течение 10 минут.\n"
            "\n📞 СВЯЗЬ:\n"
            "Если у вас есть вопросы — напишите: @cardnotlie"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'back_to_menu':
        balance = get_balance(user_id)
        message = (
            "🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n"
            "✨ Я — ваш личный таролог.\n"
            f"🎯 Ваш текущий баланс: {balance} раскладов"
        )
        keyboard = [
            [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
            [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
            [InlineKeyboardButton("📺 Подписка (+3 расклада)", callback_data='subscribe')],
            [InlineKeyboardButton("📚 История раскладов", callback_data='history_dates')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /history — показывает даты раскладов"""
    user_id = update.effective_user.id
    dates = get_reading_dates(user_id, limit=10)
    
    if not dates:
        message = "📚 ИСТОРИЯ РАСКЛАДОВ 📚\n\nУ вас пока нет сохранённых раскладов.\nСделайте первый расклад прямо сейчас!"
        keyboard = [[InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text=message, reply_markup=reply_markup)
        return
    
    message = "📚 ВЫБЕРИТЕ ДАТУ РАСКЛАДА 📚\n"
    keyboard = []
    for date_str, count in dates:
        keyboard.append([InlineKeyboardButton(f"📅 {date_str} ({count} раскладов)", callback_data=f'history_date_{date_str}')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

def main():
    init_db()
    if not TOKEN:
        print("❌ Токен не установлен")
        return
    print("✅ Бот запущен v4.0 (баланс, пакеты со скидкой, история по датам)")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()