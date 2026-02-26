import os
from dotenv import load_dotenv
from telegram.ext import Application

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

async def remove_webhook():
    app = Application.builder().token(TOKEN).build()
    await app.bot.delete_webhook()
    print("✅ Webhook удалён. Теперь polling будет работать.")
    await app.shutdown()

import asyncio
asyncio.run(remove_webhook())