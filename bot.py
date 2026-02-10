import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask
import threading

from database import init_db, add_user, check_free_used, mark_free_used, add_referral, get_referral_count, add_reading, get_readings_history, mark_subscribed, check_subscribed
from tarot_cards import get_random_cards, format_reading, get_single_card

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ v3.1"

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
                            text=f"🎉 Отлично! Ваш друг {user.first_name} присоединился!\nВы получили +1 к реферальному счёту!"
                        )
                    except: pass
        except: pass
    
    referral_count = get_referral_count(user.id)
    subscribed = check_subscribed(user.id)
    
    message = (
        "🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n\n"
        "✨ Я — ваш личный таролог, готовый раскрыть тайны будущего.\n"
        "💫 ЧТО Я МОГУ:\n"
        "• Мгновенные расклады на любые вопросы 💫\n"
        "• Глубокий анализ ситуации в любви и карьере ❤️‍🔥💼\n"
        "• Персональные советы от карт 🌟\n"
        "• История всех ваших раскладов 📚\n\n"
        "🌟 ПЕРВЫЙ РАСКЛАД — БЕСПЛАТНО!\n"
        f"🎁 Ваш баланс: {referral_count} бесплатных раскладов"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton("💫 Рефералы (+1 за друга)", callback_data='referral')],
        [InlineKeyboardButton("📺 Подписка (+3 расклада)", callback_data='subscribe')],
        [InlineKeyboardButton("📚 История раскладов", callback_data='history')],
        [InlineKeyboardButton("💳 Оплата (100₽)", callback_data='pay_info')],
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
        free_used = check_free_used(user_id)
        referral_count = get_referral_count(user_id)
        
        # Проверяем общий баланс (бесплатный + рефералы)
        has_free = (not free_used) or (referral_count > 0)
        
        if has_free:
            # Если есть бесплатный расклад — используем его
            if not free_used:
                mark_free_used(user_id)
            else:
                # Уменьшаем счётчик рефералов
                conn = sqlite3.connect('tarot_bot.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET referral_count = referral_count - 1 WHERE user_id = ?', (user_id,))
                conn.commit()
                conn.close()
            
            # Делаем расклад
            cards = get_random_cards(3)
            reading = format_reading(cards)
            add_reading(user_id, cards, reading)  # Сохраняем полный текст в историю
            
            # Отправляем расклад КАК НОВОЕ СООБЩЕНИЕ (не редактируем старое!)
            await query.message.reply_text(text=reading)
            
            # Отправляем кнопки отдельным сообщением
            keyboard = [
                [InlineKeyboardButton("🔄 Ещё один расклад", callback_data='do_tarot')],
                [InlineKeyboardButton("📚 История раскладов", callback_data='history')],
                [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                text="💫 Что дальше?",
                reply_markup=reply_markup
            )
        else:
            # Нет бесплатных раскладов — показываем оплату
            keyboard = [
                [InlineKeyboardButton("💳 Оплатить 100₽", callback_data='pay_button')],
                [InlineKeyboardButton("📚 История раскладов", callback_data='history')],
                [InlineKeyboardButton("🎁 Пригласить друга (+1)", callback_data='referral')],
                [InlineKeyboardButton("📺 Подписаться (+3)", callback_data='subscribe')],
                [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
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
            f"📊 Ваш счёт: {referral_count} бесплатных раскладов\n"
            f"💫 За каждого друга, который начнёт пользоваться ботом, вы получите +1 расклад!\n\n"
            f"📤 Просто отправьте ссылку друзьям или в соцсети!"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'subscribe':
        subscribed = check_subscribed(user_id)
        if subscribed:
            message = "✅ Вы уже подписаны на наш канал!\n💫 Бонус +3 расклада уже начислен на ваш счёт."
        else:
            message = (
                "📺 ПОДПИСКА НА КАНАЛ 📺\n\n"
                "Подпишитесь на наш эзотерический канал и получите +3 бесплатных расклада!\n\n"
                "✨ Канал: https://t.me/+5q7VJBPU4_QyMDky\n\n"
                "После подписки нажмите кнопку ниже:"
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
    
    elif query.data == 'history':
        readings = get_readings_history(user_id, limit=5)
        if not readings:
            message = "📚 ИСТОРИЯ РАСКЛАДОВ 📚\n\nУ вас пока нет сохранённых раскладов.\nСделайте первый расклад прямо сейчас!"
        else:
            message = "📚 ИСТОРИЯ ВАШИХ РАСКЛАДОВ 📚\n\n"
            for i, (cards, interpretation, positions, timestamp) in enumerate(readings, 1):
                message += f"Расклад #{i} | 📅 {timestamp[:16]}\n"
                message += f"━━━━━━━━━━━━━━━━━━━━\n"
                message += interpretation + "\n\n"
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
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
            "\nНажмите кнопку ниже, чтобы оплатить:"
        )
        keyboard = [[InlineKeyboardButton("💳 Оплатить 100₽", callback_data='pay_button')], [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'pay_button':
        message = (
            "💳 ОПЛАТА РАСКЛАДА (100 ₽) 💳\n\n"
            "✨ Выберите удобный способ оплаты:\n"
            "\n📱 СБП (мгновенный перевод):\n"
            "▫️ Банк: Райффайзен банк\n"
            "▫️ Получатель: Сергей\n"
            "▫️ Номер карты: \n"
            "▫️ Сумма: 100 ₽\n"
            "▫️ Комментарий: tarot_{user_id}\n"
            "\n🪙 Криптовалюта (USDT):\n"
            "▫️ Сеть: TRC20 (Tron)\n"
            "▫️ Адрес: \n"
            "▫️ Сумма: 1 USDT\n"
            "▫️ Мемо: tarot_{user_id}\n"
            "\n✅ ПОСЛЕ ОПЛАТЫ:\n"
            "1. Сделайте скриншот перевода или скопируйте хэш транзакции.\n"
            "2. Напишите мне с пометкой «ОПЛАТА».\n"
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
            "4. Нажмите «Ещё один расклад» для повторного гадания.\n"
            "\n💫 БЕСПЛАТНЫЙ РАСКЛАД:\n"
            "• Первый расклад — абсолютно бесплатно!\n"
            "• Дополнительные расклады — через реферальную программу или оплату.\n"
            "• За каждого приглашённого друга вы получаете +1 бесплатный расклад.\n"
            "• За подписку на канал — +3 бесплатных расклада.\n"
            "\n🎁 РЕФЕРАЛЬНАЯ ПРОГРАММА:\n"
            "• Пригласите друга по вашей ссылке.\n"
            "• Когда друг начнёт пользоваться ботом — вы получите +1 расклад.\n"
            "• Поделитесь ссылкой в соцсетях и получайте неограниченное количество раскладов!\n"
            "\n💳 ПЛАТНЫЕ РАСКЛАДЫ:\n"
            "• Стоимость: 100 ₽ за расклад.\n"
            "• Оплата через СБП или криптовалюту (USDT).\n"
            "• После оплаты напишите мне с подтверждением.\n"
            "• Расклад будет готов в течение 10 минут.\n"
            "\n📞 СВЯЗЬ:\n"
            "Если у вас есть вопросы — напишите: @cardnotlie"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'back_to_menu':
        referral_count = get_referral_count(user_id)
        message = (
            "🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n\n"
            "✨ Я — ваш личный таролог, готовый раскрыть тайны будущего.\n"
            "💫 ЧТО Я МОГУ:\n"
            "• Мгновенные расклады на любые вопросы 💫\n"
            "• Глубокий анализ ситуации в любви и карьере ❤️‍🔥💼\n"
            "• Персональные советы от карт 🌟\n"
            "• История всех ваших раскладов 📚\n"
            "\n🌟 ПЕРВЫЙ РАСКЛАД — БЕСПЛАТНО!\n"
            f"🎁 Ваш баланс: {referral_count} бесплатных раскладов"
        )
        keyboard = [
            [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
            [InlineKeyboardButton("💫 Рефералы (+1 за друга)", callback_data='referral')],
            [InlineKeyboardButton("📺 Подписка (+3 расклада)", callback_data='subscribe')],
            [InlineKeyboardButton("📚 История раскладов", callback_data='history')],
            [InlineKeyboardButton("💳 Оплата (100₽)", callback_data='pay_info')],
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
    for i, (cards, interpretation, positions, timestamp) in enumerate(readings, 1):
        message += f"Расклад #{i} | 📅 {timestamp[:16]}\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n"
        message += interpretation + "\n\n"
    
    await update.message.reply_text(text=message)

def main():
    init_db()
    if not TOKEN:
        print("❌ Токен не установлен")
        return
    print("✅ Бот запущен v3.1 (расклады остаются в чате, подписка +3, красивая оплата)")
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