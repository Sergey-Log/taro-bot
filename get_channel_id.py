from telegram.ext import Application, MessageHandler, filters
import os
from dotenv import load_dotenv

load_dotenv()

async def forward_handler(update, context):
    """Обработчик пересланных сообщений"""
    
    # Проверяем, переслано ли сообщение
    if update.message.forward_from_chat:
        chat = update.message.forward_from_chat
        print("\n" + "="*60)
        print("✅ ПОЛУЧЕН CHAT ID КАНАЛА!")
        print("="*60)
        print(f"📛 Название: {chat.title}")
        print(f"🆔 Chat ID: {chat.id}")
        print(f"🔗 Тип: {chat.type}")
        print(f"📝 Username: {chat.username if chat.username else 'Приватный канал'}")
        print("="*60)
        print("\n📋 Скопируйте этот Chat ID в handlers.py:")
        print(f"channel_id = {chat.id}")
        print("\n💡 После этого можно остановить бота (Ctrl+C)")
        print("="*60 + "\n")
    
    # Проверяем, есть ли в сообщении текст (для отладки)
    if update.message.text:
        print(f"📩 Получено сообщение: {update.message.text[:50]}...")
        print(f"🔄 Переслано: {'Да' if update.message.forward_from_chat else 'Нет'}")
        if update.message.forward_from_chat:
            print(f"🆔 ID канала: {update.message.forward_from_chat.id}")
        print("-"*40)

async def any_message_handler(update, context):
    """Обработчик любых сообщений (для отладки)"""
    print(f"💬 Сообщение от пользователя {update.effective_user.first_name}")
    if update.message.forward_from_chat:
        await forward_handler(update, context)
    else:
        print("   (не переслано из канала)")

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN:
        print("❌ Токен не найден в .env файле")
        return
    
    print("="*60)
    print("🔍 СКРИПТ ПОЛУЧЕНИЯ CHAT ID КАНАЛА")
    print("="*60)
    print("\n📋 ИНСТРУКЦИЯ:")
    print("1. ✅ Бот должен быть добавлен в канал как АДМИНИСТРАТОР")
    print("2. 📤 Отправьте ЛЮБОЕ сообщение в ваш канал")
    print("3. 🔄 Перешлите это сообщение боту в ЛИЧНЫЕ СООБЩЕНИЯ")
    print("4. 📝 Chat ID отобразится в этой консоли")
    print("5. ⏹️ Нажмите Ctrl+C для остановки после получения ID")
    print("\n⏳ Запуск бота... Ожидание сообщений...\n")
    print("="*60 + "\n")
    
    app = Application.builder().token(TOKEN).build()
    
    # Обработчик ВСЕХ сообщений
    app.add_handler(MessageHandler(filters.ALL, any_message_handler))
    
    app.run_polling(allowed_updates=['message'])

if __name__ == "__main__":
    main()