import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask
import threading

from database import init_db, add_user, check_free_used, mark_free_used, add_referral, get_referral_count, add_reading, get_readings_history
from tarot_cards import get_random_cards, format_reading, get_single_card

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ v3.0"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start — только для текстовых сообщений"""
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
                            text=f"🎉 Отлично! Ваш друг {user.first_name} присоединился!\nВы получили +1 к реферальному счёту!"
                        )
                    except: pass
        except: pass
    
    referral_count = get_referral_count(user.id)
    message = (
        "🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n\n"
        "✨ Я — ваш личный таролог, готовый раскрыть тайны будущего.\n"
        "💫 ЧТО Я МОГУ:\n"
        "• Мгновенные расклады на любые вопросы 💫\n"
        "• Глубокий анализ ситуации 🔮\n"
        "• Прогнозы на будущее 🔮\n"
        "• История всех ваших раскладов 📚\n\n"
        "🌟 ПЕРВЫЙ РАСКЛАД — БЕСПЛАТНО!\n"
        f"🎁 Ваш реферальный баланс: {referral_count} бесплатных раскладов"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton("💫 Реферальная программа", callback_data='referral')],
        [InlineKeyboardButton("📚 История раскладов", callback_data='history')],
        [InlineKeyboardButton("💳 Оплата", callback_data='pay_info')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение ТОЛЬКО если это текстовое сообщение (/start)
    if update.message:
        await update.message.reply_text(text=message, reply_markup=reply_markup)
    else:
        # Если вызван из кнопки — редактируем текущее сообщение
        query = update.callback_query
        if query:
            await query.edit_message_text(text=message, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'do_tarot':
        free_used = check_free_used(user_id)
        if not free_used:
            cards = get_random_cards(3)
            reading = format_reading(cards)
            mark_free_used(user_id)
            add_reading(user_id, cards)  # Сохраняем в историю
            keyboard = [[InlineKeyboardButton("🔄 Ещё один расклад", callback_data='do_tarot')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=reading, reply_markup=reply_markup)
        else:
            keyboard = [
                [InlineKeyboardButton("💳 Оплатить 100₽", callback_data='pay_button')],
                [InlineKeyboardButton("🎁 Пригласить друга", callback_data='referral')],
                [InlineKeyboardButton("⬅️ Назад в меню", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text="💫 У вас закончились бесплатные расклады.\n💰 Стоимость следующего расклада: 100 ₽",
                reply_markup=reply_markup
            )
    
    elif query.data == 'referral':
        ref_link = f"https://t.me/cardnotlie_bot?start={user_id}"
        referral_count = get_referral_count(user_id)
        message = (
            f"🎁 РЕФЕРАЛЬНАЯ ПРОГРАММА 🎁\n\n"
            f"✨ Ваша реферальная ссылка:\n"
            f"{ref_link}\n\n"
            f"📊 Ваш счёт: {referral_count} приглашённых друзей\n"
            f"💫 За каждого друга — 1 бесплатный расклад!\n\n"
            f"📤 Просто отправьте ссылку друзьям — когда они начнут пользоваться ботом, вы получите бонус!"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Назад в меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'history':
        readings = get_readings_history(user_id, limit=5)
        if not readings:
            message = "📚 ИСТОРИЯ РАСКЛАДОВ 📚\n\nУ вас пока нет сохранённых раскладов.\nСделайте первый расклад прямо сейчас!"
        else:
            message = "📚 ИСТОРИЯ ВАШИХ РАСКЛАДОВ 📚\n\n"
            for i, (cards, positions, timestamp) in enumerate(readings, 1):
                cards_list = cards.split(',')
                message += f"{i}. {', '.join(cards_list)}\n"
                message += f"   📅 {timestamp[:16]}\n\n"
            message += "💫 Хотите сделать новый расклад? Нажмите кнопку ниже!"
        keyboard = [[InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')], [InlineKeyboardButton("⬅️ Назад в меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'pay_info':
        message = (
            "💳 ИНФОРМАЦИЯ ОБ ОПЛАТЕ 💳\n\n"
            "💰 Стоимость одного расклада: 100 ₽\n"
            "💫 Что входит:\n"
            "• Полный расклад из 3 карт Таро\n"
            "• Подробная интерпретация каждой карты\n"
            "• Анализ в любви и карьере ❤️‍🔥💼\n"
            "• Персональный совет от таролога 🌟\n"
            "• Сохранение в историю раскладов 📚\n"
            "• Безлимитное количество раскладов после оплаты!\n"
            "\nНажмите кнопку ниже, чтобы оплатить:"
        )
        keyboard = [[InlineKeyboardButton("💳 Оплатить 100₽", callback_data='pay_button')], [InlineKeyboardButton("⬅️ Назад в меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'pay_button':
        message = (
            "💳 ОПЛАТА РАСКЛАДА (100 ₽) 💳\n\n"
            "✨ Выберите удобный способ оплаты:\n"
            "\n📱 СБП (мгновенный перевод):\n"
            "▫️ Банк: Тинькофф / Сбербанк / ВТБ / Альфа-Банк и другие с СБП\n"
            "▫️ Получатель: [ВАШЕ ИМЯ]\n"
            "▫️ Телефон: +7 999 123-45-67\n"
            "▫️ Сумма: 100 ₽\n"
            "▫️ Комментарий: tarot_{user_id}\n"
            "\n🪙 Криптовалюта (USDT):\n"
            "▫️ Сеть: TRC20 (Tron)\n"
            "▫️ Адрес: TABC1234567890abcdef1234567890\n"
            "▫️ Сумма: 1 USDT\n"
            "▫️ Мемо/Тег: tarot_{user_id}\n"
            "\n✅ ПОСЛЕ ОПЛАТЫ:\n"
            "1. Сделайте скриншот перевода или скопируйте хэш транзакции\n"
            "2. Напишите мне с пометкой «ОПЛАТА»\n"
            "3. Я сделаю для вас расклад в течение 10 минут! ✨"
        ).format(user_id=user_id)
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='pay_info')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'help':
        message = (
            "❓ ПОМОЩЬ ❓\n\n"
            "✨ КАК ПОЛЬЗОВАТЬСЯ БОТОМ:\n"
            "1. Нажмите /start для начала работы.\n"
            "2. Нажмите кнопку «Сделать расклад».\n"
            "3. Получите мгновенный расклад Таро с подробной интерпретацией.\n"
            "4. Нажмите «Ещё один расклад» для повторного гадания.\n\n"
            "💫 БЕСПЛАТНЫЙ РАСКЛАД:\n"
            "• Первый расклад — абсолютно бесплатно!\n"
            "• Дополнительные расклады — через реферальную программу или оплату.\n"
            "• За каждого приглашённого друга вы получаете 1 бесплатный расклад.\n\n"
            "🎁 РЕФЕРАЛЬНАЯ ПРОГРАММА:\n"
            "• Пригласите друга по вашей ссылке.\n"
            "• Когда друг начнёт пользоваться ботом — вы получите +1 бесплатный расклад.\n"
            "• Поделитесь ссылкой в соцсетях и получайте неограниченное количество раскладов!\n\n"
            "💳 ПЛАТНЫЕ РАСКЛАДЫ:\n"
            "• Стоимость: 100 ₽ за расклад.\n"
            "• Оплата через СБП или криптовалюту (USDT).\n"
            "• После оплаты напишите мне с подтверждением.\n"
            "• Расклад будет готов в течение 10 минут.\n"
            "\n📞 СВЯЗЬ:\n"
            "Если у вас есть вопросы или предложения — напишите мне: @ваш_никнейм"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Назад в меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'back_to_menu':
        # ИСПРАВЛЕНО: не вызываем start(), а отправляем сообщение напрямую
        referral_count = get_referral_count(user_id)
        message = (
            "🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n\n"
            "✨ Я — ваш личный таролог, готовый раскрыть тайны будущего.\n"
            "💫 ЧТО Я МОГУ:\n"
            "• Мгновенные расклады на любые вопросы 💫\n"
            "• Глубокий анализ ситуации 🔮\n"
            "• Прогнозы на будущее 🔮\n"
            "• История всех ваших раскладов 📚\n"
            "\n🌟 ПЕРВЫЙ РАСКЛАД — БЕСПЛАТНО!\n"
            f"🎁 Ваш реферальный баланс: {referral_count} бесплатных раскладов"
        )
        keyboard = [
            [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
            [InlineKeyboardButton("💫 Реферальная программа", callback_data='referral')],
            [InlineKeyboardButton("📚 История раскладов", callback_data='history')],
            [InlineKeyboardButton("💳 Оплата", callback_data='pay_info')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /history — показывает историю раскладов"""
    user_id = update.effective_user.id
    readings = get_readings_history(user_id, limit=5)
    
    if not readings:
        message = "📚 ИСТОРИЯ РАСКЛАДОВ 📚\n\nУ вас пока нет сохранённых раскладов.\nСделайте первый расклад прямо сейчас!"
        keyboard = [[InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text=message, reply_markup=reply_markup)
        return
    
    message = "📚 ИСТОРИЯ ВАШИХ РАСКЛАДОВ 📚\n\n"
    for i, (cards, positions, timestamp) in enumerate(readings, 1):
        cards_list = cards.split(',')
        message += f"{i}. {', '.join(cards_list)}\n"
        message += f"   📅 {timestamp[:16]}\n\n"
    message += "💫 Хотите сделать новый расклад? Напишите /start!"
    
    await update.message.reply_text(text=message)

def main():
    init_db()
    if not TOKEN:
        print("❌ Токен не установлен")
        return
    print("✅ Бот запущен v3.0 (история, оплата, красивые тексты)")
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