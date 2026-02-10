import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask
import threading

from database import init_db, add_user, check_free_used, mark_free_used, add_referral, get_referral_count
from tarot_cards import get_random_cards, format_reading, get_single_card

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask приложение для проверки работы
app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ Бот работает! Таро бот @cardnotlie_bot"

# Приветственное сообщение
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    args = context.args
    
    # Добавляем пользователя в базу
    add_user(user.id, user.username, user.first_name)
    
    # Проверяем реферальную ссылку
    if args:
        try:
            referrer_id = int(args[0])
            if referrer_id != user.id:
                if add_referral(referrer_id, user.id):
                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 Отлично! Ваш друг {user.first_name} присоединился!\n"
                                 f"Вы получили +1 к реферальному счёту!"
                        )
                    except:
                        pass
        except (ValueError, IndexError):
            pass
    
    # Получаем количество рефералов
    referral_count = get_referral_count(user.id)
    
    # Формируем приветственное сообщение
    message = (
        "🔮 *ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО!* 🔮\n"
        "✨ Я — ваш личный таролог, готовый раскрыть тайны будущего.\n\n"
        "*💫 ЧТО Я МОГУ:*\n"
        "• Мгновенные расклады на любые вопросы\\n"
        "• Глубокий анализ ситуации\\n"
        "• Прогнозы на будущее\\n\\n"
        "*🌟 ПЕРВЫЙ РАСКЛАД — БЕСПЛАТНО!*\n"
        f"🎁 Ваш реферальный баланс: *{referral_count}* бесплатных раскладов\\n\\n"
        "🎯 Чтобы начать, нажмите кнопку ниже!"
    )
    
    # Создаем кнопки
    keyboard = [
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton("💫 Реферальная программа", callback_data='referral')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=message,
        parse_mode='MarkdownV2',
        reply_markup=reply_markup
    )

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == 'do_tarot':
        # Проверяем, использовал ли пользователь бесплатный расклад
        free_used = check_free_used(user_id)
        
        if not free_used:
            # Делаем бесплатный расклад
            cards = get_random_cards(3)
            reading = format_reading(cards)
            mark_free_used(user_id)
            
            # Отправляем расклад с кнопкой для нового расклада
            keyboard = [[InlineKeyboardButton("🔄 Ещё один расклад", callback_data='do_tarot')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=reading,
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )
        else:
            # Пользователь уже использовал бесплатный расклад
            keyboard = [
                [InlineKeyboardButton("💳 Оплатить 100₽", callback_data='pay_button')],
                [InlineKeyboardButton("🎁 Пригласить друга", callback_data='referral')],
                [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text="💫 У вас закончились бесплатные расклады.\\n\\n"
                     "💰 Стоимость следующего расклада: 100 ₽\\n"
                     "Выберите способ получения расклада:",
                reply_markup=reply_markup
            )
    
    elif query.data == 'referral':
        # Показываем реферальную программу
        ref_link = f"https://t.me/cardnotlie_bot?start={user_id}"
        referral_count = get_referral_count(user_id)
        
        message = (
            f"🎁 *РЕФЕРАЛЬНАЯ ПРОГРАММА* 🎁\\n\\n"
            f"✨ Ваша реферальная ссылка:\\n"
            f"`{ref_link}`\\n\\n"
            f"📊 Ваш счёт: *{referral_count}* приглашённых друзей\\n"
            f"💫 За каждого друга — *1 бесплатный расклад!*\\n\\n"
            f"📤 Просто отправьте ссылку друзьям — когда они начнут пользоваться ботом, вы получите бонус!"
        )
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад в меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message,
            parse_mode='MarkdownV2',
            reply_markup=reply_markup
        )
    
    elif query.data == 'help':
        # Показываем помощь
        message = (
            "❓ *ПОМОЩЬ* ❓\\n\\n"
            "*✨ Как пользоваться ботом:*\\n"
            "1️⃣ Нажмите /start для начала работы\\n"
            "2️⃣ Нажмите кнопку «Сделать расклад»\\n"
            "3️⃣ Получите мгновенный расклад Таро\\n\\n"
            
            "*💫 Бесплатный расклад:*\\n"
            "• Первый расклад — бесплатно\\n"
            "• Дополнительные — через реферальную программу\\n\\n"
            
            "*🎁 Реферальная программа:*\\n"
            "• Пригласите друга по вашей ссылке\\n"
            "• За каждого друга — 1 бесплатный расклад\\n\\n"
            
            "*💳 Платные расклады:*\\n"
            "• Стоимость: 100 ₽ за расклад\\n"
            "• Напишите /pay для оплаты\\n\\n"
            
            "*📞 Связь:*\\n"
            "Если есть вопросы — напишите @ваш_никнейм"
        )
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад в меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message,
            parse_mode='MarkdownV2',
            reply_markup=reply_markup
        )
    
    elif query.data == 'pay_button':
        # Показываем оплату
        message = (
            "💳 *ОПЛАТА РАСКЛАДА (100 ₽)*\\n\\n"
            "*Выберите способ оплаты:*\\n\\n"
            "📱 *СБП (мгновенно):*\\n"
            "▫️ Получатель: [ВАШЕ ИМЯ]\\n"
            "▫️ Телефон: [ВАШ НОМЕР]\\n"
            "▫️ Сумма: 100 ₽\\n"
            "▫️ Комментарий: tarot_{user_id}\\n\\n"
            
            "🪙 *Криптовалюта (USDT):*\\n"
            "▫️ Сеть: TRC20\\n"
            "▫️ Кошелёк: [ВАШ КОШЕЛЁК]\\n"
            "▫️ Сумма: 1 USDT\\n"
            "▫️ Мемо: tarot_{user_id}\\n\\n"
            
            "✅ *После оплаты* пришлите сюда скриншот или хэш транзакции — и я сделаю для вас расклад!"
        ).format(user_id=user_id)
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='do_tarot')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message,
            parse_mode='MarkdownV2',
            reply_markup=reply_markup
        )
    
    elif query.data == 'back_to_menu':
        # Возвращаемся в главное меню
        referral_count = get_referral_count(user_id)
        
        message = (
            "🔮 *ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО!* 🔮\\n"
            "✨ Я — ваш личный таролог, готовый раскрыть тайны будущего.\\n\\n"
            "*💫 ЧТО Я МОГУ:*\\n"
            "• Мгновенные расклады на любые вопросы\\n"
            "• Глубокий анализ ситуации\\n"
            "• Прогнозы на будущее\\n\\n"
            "*🌟 ПЕРВЫЙ РАСКЛАД — БЕСПЛАТНО!*\\n"
            f"🎁 Ваш реферальный баланс: *{referral_count}* бесплатных раскладов\\n\\n"
            "🎯 Чтобы начать, нажмите кнопку ниже!"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
            [InlineKeyboardButton("💫 Реферальная программа", callback_data='referral')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message,
            parse_mode='MarkdownV2',
            reply_markup=reply_markup
        )

# Команда оплаты
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /pay — реальная оплата"""
    user_id = update.effective_user.id
    
    message = (
        "💳 *ОПЛАТА РАСКЛАДА (100 ₽)* 💳\\n\\n"
        "✨ Выберите удобный способ оплаты:\\n\\n"
        
        "📱 *СБП (мгновенный перевод):*\\n"
        "▫️ Банк: Тинькофф / Сбербанк / ВТБ\\n"
        "▫️ Получатель: [ВАШЕ ИМЯ]\\n"
        "▫️ Телефон: +7 999 123-45-67\\n"
        "▫️ Сумма: 100 ₽\\n"
        "▫️ Комментарий: `tarot_{user_id}`\\n\\n"
        
        "🪙 *Криптовалюта (USDT):*\\n"
        "▫️ Сеть: TRC20 (Tron)\\n"
        "▫️ Адрес: `TABC1234567890abcdef1234567890`\\n"
        "▫️ Сумма: 1 USDT\\n"
        "▫️ Мемо/Тег: `tarot_{user_id}`\\n\\n"
        
        "✅ *После оплаты:*\\n"
        "1\\. Сделайте скриншот перевода или скопируйте хэш транзакции\\n"
        "2\\. Напишите сюда с пометкой *«ОПЛАТА»*\\n"
        "3\\. Я сделаю для вас расклад в течение 10 минут! ✨"
    ).format(user_id=user_id)
    
    await update.message.reply_text(
        text=message,
        parse_mode='MarkdownV2'
    )

# Команда помощи
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    message = (
        "❓ *ПОМОЩЬ* ❓\\n\\n"
        "*✨ Как пользоваться ботом:*\\n"
        "1️⃣ Нажмите /start для начала работы\\n"
        "2️⃣ Нажмите кнопку «Сделать расклад»\\n"
        "3️⃣ Получите мгновенный расклад Таро\\n\\n"
        
        "*💫 Бесплатный расклад:*\\n"
        "• Первый расклад — бесплатно\\n"
        "• Дополнительные — через реферальную программу\\n\\n"
        
        "*🎁 Реферальная программа:*\\n"
        "• Пригласите друга по вашей ссылке\\n"
        "• За каждого друга — 1 бесплатный расклад\\n\\n"
        
        "*💳 Платные расклады:*\\n"
        "• Стоимость: 100 ₽ за расклад\\n"
        "• Напишите /pay для оплаты\\n\\n"
        
        "*📞 Связь:*\\n"
        "Если есть вопросы — напишите @ваш_никнейм"
    )
    await update.message.reply_text(
        text=message,
        parse_mode='MarkdownV2'
    )

# Команда /deep — глубокий анализ
async def deep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /deep — глубокий анализ"""
    user_id = update.effective_user.id
    free_used = check_free_used(user_id)
    
    if not free_used:
        # Бесплатный глубокий расклад
        cards = get_random_cards(5)
        positions = [
            "🎴 *Ситуация сейчас*",
            "🎴 *Скрытые причины*",
            "🎴 *Ваши действия*",
            "🎴 *Внешние влияния*",
            "🎴 *Итоговый результат*"
        ]
        reading = format_reading(cards, positions)
        mark_free_used(user_id)
        
        await update.message.reply_text(
            text=reading,
            parse_mode='MarkdownV2'
        )
    else:
        # Платный глубокий расклад
        message = (
            "💫 *ГЛУБОКИЙ АНАЛИЗ* 🔮\\n\\n"
            "Это расширенный расклад из 5 карт с детальным разбором ситуации.\\n\\n"
            "💰 Стоимость: 200 ₽\\n"
            "Напишите /pay для оплаты."
        )
        await update.message.reply_text(
            text=message,
            parse_mode='MarkdownV2'
        )

# Команда /card — карта дня
async def card_of_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /card — карта дня"""
    card_name, card_meaning = get_single_card()
    
    message = (
        "🌅 *КАРТА ДНЯ* 🌅\\n\\n"
        f"🎴 *{card_name}*\\n\\n"
        f"💫 {card_meaning}\\n\\n"
        "✨ *Совет карты на сегодня:*\\n"
        "▫️ Будьте открыты к новым возможностям\\n"
        "▫️ Доверяйте своей интуиции\\n"
        "▫️ Примите то, что не можете изменить"
    )
    
    await update.message.reply_text(
        text=message,
        parse_mode='MarkdownV2'
    )

# Основная функция запуска
def main():
    """Основная функция запуска бота"""
    # Инициализация базы данных
    init_db()
    
    # Проверка токена
    if not TOKEN or TOKEN == "ВАШ_ТОКЕН_ОТ_BOTFATHER":
        print("❌ ОШИБКА: Не установлен токен бота!")
        print("Добавьте токен в переменные окружения:")
        print("BOT_TOKEN = ваш_токен_от_BotFather")
        return
    
    print("✅ Токен загружен")
    print("✅ Инициализация бота...")
    
    # Создание приложения
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pay", pay))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("deep", deep))
    application.add_handler(CommandHandler("card", card_of_day))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Бот запущен! Нажмите Ctrl+C для остановки")
    
    # Запуск бота
    application.run_polling()

# Запуск веб-сервера в отдельном потоке
def run_flask():
    """Запуск веб-сервера Flask"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Запускаем веб-сервер в фоне
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Запускаем бота
    main()