import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from flask import Flask
import threading

from handlers import start_handler, button_handler, history_command, terms_command, ask_name, ask_birthdate
from utils import init_db

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ v5.4"

@app.route('/webhook', methods=['POST'])
def webhook():
    from handlers import process_webhook
    return process_webhook()

def main():
    init_db()
    if not TOKEN:
        print("❌ Токен не установлен")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков
    application.add_handler(start_handler)
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("terms", terms_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Бот запущен v5.4")
    application.run_polling()

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()