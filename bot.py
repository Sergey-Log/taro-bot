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
        "🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n\n"
        "✨ Я — ваш личный таролог, готовый раскрыть тайны будущего.\n\n"
        "💫 ЧТО Я МОГУ:\n"
        "• Мгновенные расклады на любые вопросы\n"
        "• Глубокий анализ ситуации\n"
        "• Прогнозы на будущее\n\n"
        "🌟 ПЕРВЫЙ РАСКЛАД — БЕСПЛАТНО!\n"
        f"🎁 Ваш реферальный баланс: {referral_count} бесплатных раскладов\n\n"
        "🎯 Чтобы начать, нажмите кнопку ниже!"
    )
    
    # Создаем кнопки
    keyboard = [
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton("💫 Реферальная программа", callback_data='referral')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup)

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
            await query.edit_message_text(
                text=reading,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Ещё один расклад", callback_data='do_tarot')
                ]])
            )
        else:
            # Пользователь уже использовал бесплатный расклад
            await query.edit_message_text(
                text="💫 У вас закончились бесплатные расклады.\n\n"
                     "Стоимость следующего расклада: 100 ₽\n"
                     "Для оплаты напишите /pay",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎁 Пригласить друга за бесплатный расклад", callback_data='referral')
                ]])
            )
    
    elif query.data == 'referral':
        # Показываем реферальную программу
        ref_link = f"https://t.me/cardnotlie_bot?start={user_id}"
        referral_count = get_referral_count(user_id)
        
        message = (
            f"🎁 РЕФЕРАЛЬНАЯ ПРОГРАММА 🎁\n\n"
            f"Ваша реферальная ссылка:\n"
            f"`{ref_link}`\n\n"
            f"📊 Ваш счёт: {referral_count} приглашённых друзей\n"
            f"💫 За каждого друга вы получаете 1 бесплатный расклад!\n\n"
            f"Просто отправьте ссылку друзьям — когда они начнут пользоваться ботом, вы получите бонус!"
        )
        
        await query.edit_message_text(
            text=message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')
            ]])
        )
    
    elif query.data == 'help':
        # Показываем помощь
        message = (
            "❓ ПОМОЩЬ ❓\n\n"
            "✨ Как пользоваться ботом:\n"
            "1. Нажмите /start для начала работы\\n"
            "2. Нажмите кнопку «Сделать расклад»\\n"
            "3. Получите мгновенный расклад Таро\\n\\n"
            
            "💫 Бесплатный расклад:\n"
            "• Первый расклад — бесплатно\\n"
            "• Дополнительные расклады — через реферальную программу\\n\\n"
            
            "🎁 Реферальная программа:\n"
            "• Пригласите друга по вашей ссылке\\n"
            "• За каждого друга — 1 бесплатный расклад\\n\\n"
            
            "💳 Платные расклады:\n"
            "• Стоимость: 100 ₽ за расклад\\n"
            "• Напишите /pay для оплаты\\n\\n"
            
            "📞 Связь:\n"
            "Если у вас есть вопросы, напишите @ваш_никнейм"
        )
        
        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')
            ]])
        )
    
    elif query.data == 'back_to_menu':
        # Возвращаемся в главное меню
        await start(update, context)

# Команда оплаты
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /pay"""
    message = (
        "💳 ОПЛАТА РАСКЛАДА (100 ₽)\n\n"
        "Выберите способ оплаты:\n"
        "• СБП / Перевод на карту: напишите @ваш_никнейм для получения реквизитов\\n"
        "• USDT (TRC20): напишите @ваш_никнейм для получения кошелька\\n\\n"
        "После оплаты напишите @ваш_никнейм с подтверждением — и я сделаю для вас расклад! ✨"
    )
    await update.message.reply_text(message)

# Команда помощи
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    message = (
        "❓ ПОМОЩЬ ❓\n\n"
        "✨ Как пользоваться ботом:\n"
        "1. Нажмите /start для начала работы\\n"
        "2. Нажмите кнопку «Сделать расклад»\\n"
        "3. Получите мгновенный расклад Таро\\n\\n"
        
        "💫 Бесплатный расклад:\n"
        "• Первый расклад — бесплатно\\n"
        "• Дополнительные расклады — через реферальную программу\\n\\n"
        
        "🎁 Реферальная программа:\n"
        "• Пригласите друга по вашей ссылке\\n"
        "• За каждого друга — 1 бесплатный расклад\\n\\n"
        
        "💳 Платные расклады:\n"
        "• Стоимость: 100 ₽ за расклад\\n"
        "• Напишите /pay для оплаты\\n\\n"
        
        "📞 Связь:\n"
        "Если у вас есть вопросы, напишите @ваш_никнейм"
    )
    await update.message.reply_text(message)

# Основная функция запуска
def main():
    """Основная функция запуска бота"""
    # Инициализация базы данных
    init_db()
    
    # Проверка токена
    if not TOKEN or TOKEN == "ВАШ_ТОКЕН_ОТ_BOTFATHER":
        print("❌ ОШИБКА: Не установлен токен бота!")
        print("Добавьте токен в переменные окружения на Render:")
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
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Бот запущен! Нажмите Ctrl+C для остановки")
    
    # Запуск бота
    application.run_polling()

# Запуск веб-сервера в отдельном потоке (для проверки на Render)
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