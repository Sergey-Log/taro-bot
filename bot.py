import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import BotCommand
from flask import Flask
import threading
from handlers import (
    start_handler, button_handler, history_command, terms_command,
    daily_command, balance_command, help_command, menu_command,
    reading_step_1_handler, reading_step_2_handler
)
from utils import init_db

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ v5.14"

@app.route('/webhook', methods=['POST'])
def webhook():
    return "OK", 200

async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start", "🔮 Начать работу с ботом"),
        BotCommand("menu", "🏠 Главное меню"),
        BotCommand("daily", "🌅 Карта дня (бесплатно)"),
        BotCommand("balance", "⚖️ Проверить баланс"),
        BotCommand("help", "❓ Помощь и инструкции")
    ])

def main():
    init_db()
    if not TOKEN:
        print("❌ Токен не установлен")
        return
    
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    # Регистрация ВСЕХ обработчиков
    application.add_handler(start_handler)
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("daily", daily_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("terms", terms_command))

    # Глобальные обработчики для кнопок "Далее"
    application.add_handler(CallbackQueryHandler(reading_step_1_handler, pattern='^reading_step_1$'))
    application.add_handler(CallbackQueryHandler(reading_step_2_handler, pattern='^reading_step_2$'))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("✅ Бот запущен v5.14")
    
    # 🔧 ИСПРАВЛЕНИЕ CONFLICT ERROR:
    application.run_polling(
        allowed_updates=['message', 'callback_query'],
        drop_pending_updates=True  # ← Очищает очередь старых обновлений
    )

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()