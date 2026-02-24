from telegram.ext import Application
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def get_channel_id():
    """Получить Chat ID канала по invite link"""
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN:
        print("❌ Токен не найден в .env файле")
        return
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    try:
        # Ваш invite link канала
        invite_link = "+5q7VJBPU4_QyMDky"
        
        # Получаем информацию о чате
        chat = await app.bot.get_chat(chat_id=f"@{invite_link}")
        
        print("\n" + "="*50)
        print(f"✅ Chat ID канала: {chat.id}")
        print(f"📛 Название: {chat.title}")
        print(f"🔗 Username: {chat.username}")
        print("="*50 + "\n")
        print("📋 Скопируйте этот Chat ID и вставьте в handlers.py:")
        print(f"channel_id = {chat.id}")
        print("\n")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("\n💡 Убедитесь что:")
        print("1. Бот добавлен в канал как АДМИНИСТРАТОР")
        print("2. Токен бота правильный в .env файле")
        print("3. Invite link правильный\n")
    
    await app.shutdown()

if __name__ == "__main__":
    print("🔍 Получаем Chat ID канала...\n")
    asyncio.run(get_channel_id())