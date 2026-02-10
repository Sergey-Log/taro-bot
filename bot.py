import os
import logging
import sqlite3
import requests
import json
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request
import threading

from database import init_db, add_user, get_balance, decrease_balance, increase_balance, add_referral, mark_subscribed, check_subscribed, get_saved_slots, save_reading, get_saved_reading, delete_saved_reading, create_payment, complete_payment
from tarot_cards import get_random_cards, format_reading, get_single_card

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
NOWPAYMENTS_KEY = os.getenv("NOWPAYMENTS_KEY", "YOUR_API_KEY_HERE")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def health_check():
    return "✅ v5.0"

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Вебхук для автоматического зачисления криптовалюты"""
    try:
        data = request.get_json()
        
        payment_id = data.get('payment_id')
        status = data.get('payment_status')
        tx_hash = data.get('tx_hash', 'N/A')
        
        if status == 'confirmed' and payment_id:
            user_id, pack_size = complete_payment(payment_id, tx_hash)
            if user_id:
                # Отправляем уведомление пользователю
                await application.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ Оплата получена! ✨\n\n"
                         f"💰 На ваш баланс зачислено {pack_size} раскладов.\n"
                         f"🧾 Транзакция: {tx_hash[:10]}...\n\n"
                         f"🎴 Готовы к новому гаданию?"
                )
                return "OK", 200
        
        return "Ignored", 200
    except Exception as e:
        print(f"Ошибка вебхука: {e}")
        return "Error", 500

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    add_user(user.id, user.username, user.first_name)
    
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
    message = f"🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n✨ Ваш баланс: {balance} раскладов"
    
    keyboard = [
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
        [InlineKeyboardButton("📺 Подписка (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(text=message, reply_markup=reply_markup)
    else:
        query = update.callback_query
        if query:
            await query.edit_message_text(text=message, reply_markup=reply_markup)

async def create_crypto_invoice(user_id, pack_size, currency="USDT"):
    """Создать инвойс для оплаты криптовалютой"""
    prices = {1: 100, 3: 285, 7: 630, 13: 1105}
    amount_rub = prices.get(pack_size, 100)
    
    # Проверка наличия ключа
    if not NOWPAYMENTS_KEY or NOWPAYMENTS_KEY == "YOUR_API_KEY_HERE":
        print("❌ ОШИБКА: NOWPAYMENTS_KEY не установлен в переменных окружения!")
        return None, None, None, None
    
    # Проверка наличия вебхука
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        print("❌ ОШИБКА: WEBHOOK_URL не установлен в переменных окружения!")
        return None, None, None, None
    
    try:
        headers = {
            "X-API-Key": NOWPAYMENTS_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "price_amount": amount_rub,
            "price_currency": "RUB",
            "pay_currency": currency,
            "order_id": f"taro_{user_id}_{pack_size}",
            "order_description": f"Пакет {pack_size} раскладов Таро",
            "success_url": "https://t.me/cardnotlie_bot",
            "ipn_callback_url": webhook_url
        }
        
        response = requests.post(
            "https://api.nowpayments.io/v1/invoice",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 201:
            invoice = response.json()
            payment_id = invoice['id']
            invoice_url = invoice['invoice_url']
            pay_amount = invoice['pay_amount']
            pay_currency = invoice['pay_currency']
            
            create_payment(user_id, amount_rub, pack_size, payment_id, pay_currency, pay_amount)
            
            print(f"✅ Инвойс создан: {payment_id} | Сумма: {pay_amount} {pay_currency}")
            return payment_id, invoice_url, pay_amount, pay_currency
        else:
            error_msg = response.json().get('message', 'Неизвестная ошибка')
            print(f"❌ Ошибка NOWPayments ({response.status_code}): {error_msg}")
            return None, None, None, None
            
    except requests.exceptions.Timeout:
        print("❌ Таймаут при создании инвойса (проверьте интернет)")
        return None, None, None, None
    except Exception as e:
        print(f"❌ Исключение при создании инвойса: {type(e).__name__} - {e}")
        return None, None, None, None

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'do_tarot':
        balance = get_balance(user_id)
        
        if balance > 0:
            decrease_balance(user_id, 1)
            cards = get_random_cards(3)
            reading = format_reading(cards)
            new_balance = get_balance(user_id)
            
            if 'pending_readings' not in context.user_data:
                context.user_data['pending_readings'] = {}
            context.user_data['pending_readings'][user_id] = (cards, reading)
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=reading
            )
            
            keyboard = [
                [InlineKeyboardButton("💾 Сохранить расклад", callback_data='save_last_reading')],
                [InlineKeyboardButton("🔄 Ещё один расклад", callback_data='do_tarot')],
                [InlineKeyboardButton(f"⚖️ Баланс: {new_balance}", callback_data='balance')],
                [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="💫 Расклад готов! 💾 Сохраните его, чтобы не потерять.",
                reply_markup=reply_markup
            )
        else:
            keyboard = [
                [InlineKeyboardButton("💳 Купить расклады", callback_data='buy_packs')],
                [InlineKeyboardButton("📺 Подписаться (+3)", callback_data='subscribe')],
                [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text="💫 У вас закончились расклады.\n💰 Пополните баланс или получите бонусы!",
                reply_markup=reply_markup
            )
    
    elif query.data == 'save_last_reading':
        if 'pending_readings' in context.user_data and user_id in context.user_data['pending_readings']:
            cards, reading_text = context.user_data['pending_readings'][user_id]
            slots = get_saved_slots(user_id)
            free_slots = [i for i in range(1, 4) if i not in slots]
            
            if free_slots:
                slot = save_reading(user_id, cards, reading_text, free_slots[0])
                message = f"✅ Расклад сохранён в ячейку #{slot}!"
                keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text=message, reply_markup=reply_markup)
                del context.user_data['pending_readings'][user_id]
            else:
                message = "⚠️ Все 3 ячейки заняты. Сначала удалите старый расклад:"
                keyboard = []
                for slot_num, timestamp in slots.items():
                    keyboard.append([InlineKeyboardButton(f"❌ Ячейка #{slot_num} ({timestamp})", callback_data=f'delete_slot_{slot_num}')])
                keyboard.append([InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text=message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="❌ Нет расклада для сохранения. Сначала сделайте расклад!")
    
    elif query.data.startswith('delete_slot_'):
        slot_num = int(query.data.split('_')[2])
        if delete_saved_reading(user_id, slot_num):
            message = f"✅ Расклад из ячейки #{slot_num} удалён."
        else:
            message = "❌ Ошибка удаления."
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'saved_readings':
        slots = get_saved_slots(user_id)
        occupied = len(slots)
        free = 3 - occupied
        
        message = f"🗄️ МОИ СОХРАНЁННЫЕ РАСКЛАДЫ 🗄️\n📦 Доступно ячеек для сохранения: {occupied}/3\n"
        if free > 0:
            message += f"✨ Свободно ячеек: {free}\n\n"
        else:
            message += "⚠️ Все ячейки заняты. Чтобы сохранить новый расклад, сначала удалите старый.\n\n"
        
        if not slots:
            message += "У вас пока нет сохранённых раскладов.\nСделайте расклад и нажмите «💾 Сохранить»!"
            keyboard = [[InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')], [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=message, reply_markup=reply_markup)
            return
        
        keyboard = []
        for slot_num in sorted(slots.keys()):
            timestamp = slots[slot_num]
            keyboard.append([InlineKeyboardButton(f"📦 Ячейка #{slot_num} ({timestamp})", callback_data=f'view_slot_{slot_num}')])
        keyboard.append([InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data.startswith('view_slot_'):
        slot_num = int(query.data.split('_')[2])
        reading = get_saved_reading(user_id, slot_num)
        if reading:
            cards_str, interpretation, timestamp = reading
            message = f"📦 РАСКЛАД ИЗ ЯЧЕЙКИ #{slot_num}\n📅 {timestamp[:16]}\n\n{interpretation}"
            keyboard = [[InlineKeyboardButton("❌ Удалить этот расклад", callback_data=f'delete_slot_{slot_num}')], [InlineKeyboardButton("⬅️ Назад к списку", callback_data='saved_readings')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="❌ Расклад не найден.")
    
    elif query.data == 'balance':
        balance = get_balance(user_id)
        message = (
            f"⚖️ ВАШ ТЕКУЩИЙ БАЛАНС ⚖️\n"
            f"\n🔮 Доступно раскладов: {balance}\n"
            f"\n✨ Как получить больше раскладов:\n"
            f"• Пригласите друга — +1 расклад 🎁\n"
            f"• Подпишитесь на канал — +3 расклада 📺\n"
            f"• Купите пакет раскладов со скидкой 💳"
        )
        keyboard = [
            [InlineKeyboardButton("💳 Купить расклады", callback_data='buy_packs')],
            [InlineKeyboardButton("💫 Пригласить друга", callback_data='referral')],
            [InlineKeyboardButton("📺 Подписаться (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'referral':
        ref_link = f"https://t.me/cardnotlie_bot?start={user_id}"
        referral_count = get_referral_count(user_id)
        message = (
            f"🎁 РЕФЕРАЛЬНАЯ ПРОГРАММА 🎁\n\n"
            f"✨ Ваша реферальная ссылка:\n"
            f"{ref_link}\n\n"
            f"📊 Приглашено друзей: {referral_count}\n"
            f"💫 За каждого друга — +1 бесплатный расклад!\n\n"
            f"📤 Просто отправьте ссылку друзьям или в соцсети!"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'buy_packs':
    message = (
        "💳 СПОСОБЫ ОПЛАТЫ 💳\n"
        "\nВыберите удобный способ:\n"
        "\n💎 Криптовалюта — автоматическое зачисление после оплаты ✅\n"
        "🏦 Банковская карта — требуется ручная проверка скриншота ⏳"
    )
    keyboard = [
        [InlineKeyboardButton("💎 Криптовалюта (авто)", callback_data='crypto_packs')],
        [InlineKeyboardButton("🏦 Банковская карта", callback_data='card_packs')],
        [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'crypto_packs':
        message = (
            "💎 ПАКЕТЫ КРИПТОВАЛЮТОЙ 💎\n"
            "\n✨ Выберите пакет со скидкой:\n"
            "\n🎴 1 расклад — ~1.2 USDT (100₽)\n"
            "🎴 3 расклада — ~3.4 USDT (285₽, -5%)\n"
            "🎴 7 раскладов — ~7.5 USDT (630₽, -10%)\n"
            "🎴 13 раскладов — ~13.2 USDT (1105₽, -15%)"
        )
        keyboard = [
            [InlineKeyboardButton("1 расклад", callback_data='crypto_1')],
            [InlineKeyboardButton("3 расклада (-5%)", callback_data='crypto_3')],
            [InlineKeyboardButton("7 раскладов (-10%)", callback_data='crypto_7')],
            [InlineKeyboardButton("13 раскладов (-15%)", callback_data='crypto_13')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='buy_packs')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data.startswith('crypto_'):
        pack_size = int(query.data.split('_')[1])
        payment_id, invoice_url, pay_amount, pay_currency = await create_crypto_invoice(user_id, pack_size, "USDT")
        
        if payment_id:
            message = (
                f"💎 ОПЛАТА КРИПТОВАЛЮТОЙ 💎\n"
                f"\n📦 Пакет: {pack_size} раскладов (скидка до 15%)\n"
                f"💰 Сумма: {pay_amount:.4f} {pay_currency}\n\n"
                f"👇 Для оплаты:\n"
                f"1. Нажмите кнопку «🔗 Перейти к оплате» ниже.\n"
                f"2. Откройте кошелёк и отправьте точную сумму.\n"
                f"3. После подтверждения транзакции расклады автоматически зачислятся!\n"
                f"\n⚠️ Оплата действительна 24 часа."
            )
            keyboard = [
                [InlineKeyboardButton("🔗 Перейти к оплате", url=invoice_url)],
                [InlineKeyboardButton("⬅️ Назад к пакетам", callback_data='crypto_packs')],
                [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="❌ Ошибка создания платежа. Попробуйте позже или обратитесь в поддержку @jobphone_admin")
    
    elif query.data == 'card_packs':
        message = (
            "💳 ПАКЕТЫ РАСКЛАДОВ 💳\n"
            "\n✨ Выберите пакет со скидкой:\n"
            "\n🎴 1 расклад — 100 ₽\n"
            "   Идеально для разового гадания.\n"
            "\n🎴 3 расклада — 285 ₽ (-5%)\n"
            "   Экономия 15 ₽.\n"
            "\n🎴 7 раскладов — 630 ₽ (-10%)\n"
            "   Экономия 70 ₽.\n"
            "\n🎴 13 раскладов — 1 105 ₽ (-15%)\n"
            "   Экономия 195 ₽."
        )
        keyboard = [
            [InlineKeyboardButton("1 расклад — 100₽", callback_data='buy_1')],
            [InlineKeyboardButton("3 расклада — 285₽ (-5%)", callback_data='buy_3')],
            [InlineKeyboardButton("7 раскладов — 630₽ (-10%)", callback_data='buy_7')],
            [InlineKeyboardButton("13 раскладов — 1 105₽ (-15%)", callback_data='buy_13')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='buy_packs')]
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
            f"▫️ Банк: Райффайзенбанк.\n"
            f"▫️ Номер карты: \n"
            f"▫️ Получатель: Сергей Л.\n"
            f"▫️ Сумма: {price} ₽.\n"
            f"\n✅ ПОСЛЕ ОПЛАТЫ:\n"
            f"1. Сделайте скриншот перевода.\n"
            f"2. Напишите в поддержку @jobphone_admin с пометкой «ОПЛАТА».\n"
            f"3. Мы начислим {pack_size} раскладов на ваш баланс в течение 10 минут! ✨\n"
            f"\nℹ️ Подробнее об условиях оплаты: /terms"
        )
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к пакетам", callback_data='card_packs')],
            [InlineKeyboardButton("📄 Условия оплаты", callback_data='terms')],
            [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'terms' or query.data == 'terms_button':
        message = (
            "📄 УСЛОВИЯ ОПЛАТЫ И СОГЛАСИЕ 📄\n"
            "\n💫 ВАЖНО: любая оплата в этом боте является ДОБРОВОЛЬНЫМ ДОНАТОМ.\n"
            "Расклады Таро предоставляются в развлекательных целях.\n"
            "Интерпретации карт не являются предсказанием будущего и не заменяют консультацию специалиста.\n"
            "\n✅ Нажимая «Оплатить», вы соглашаетесь с тем, что:\n"
            "• Оплата добровольная и необязательная.\n"
            "• Расклады носят развлекательный характер.\n"
            "• Вы совершаете платёж по собственной воле без принуждения.\n"
            "• Возврат средств не предусмотрен (добровольный донат).\n"
            "\n✨ Спасибо за поддержку проекта! 💫"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Назад к оплате", callback_data='buy_packs')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'subscribe':
        subscribed = check_subscribed(user_id)
        if subscribed:
            message = "✅ Вы уже подписаны на наш канал!\n💫 Бонус +3 расклада уже начислен."
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
            message = "🎉 Ура! Вы подписались на канал!\n✨ Бонус +3 бесплатных расклада начислен на ваш счёт!"
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'help':
        message = (
            "❓ ПОМОЩЬ ❓\n"
            "\n✨ КАК ПОЛЬЗОВАТЬСЯ БОТОМ:\n"
            "1. Нажмите «Сделать расклад».\n"
            "2. Получите мгновенный расклад из 3 карт.\n"
            "3. Нажмите «💾 Сохранить расклад», чтобы не потерять его.\n"
            "\n🗄️ СОХРАНЕНИЕ РАСКЛАДОВ:\n"
            "• У вас есть 3 ячейки для сохранения раскладов.\n"
            "• Расклады НЕ сохраняются автоматически — только по вашему выбору.\n"
            "• Если все ячейки заняты — сначала удалите старый расклад.\n"
            "\n⚖️ БАЛАНС:\n"
            "• При регистрации: 1 бесплатный расклад.\n"
            "• За друга: +1 расклад.\n"
            "• За подписку: +3 расклада.\n"
            "• Покупка пакетов со скидкой до 15%.\n"
            "\n💳 ОПЛАТА:\n"
            "• Криптовалюта (автоматически через вебхук).\n"
            "• Банковская карта (вручную, через поддержку).\n"
            "• Подробнее об условиях: /terms"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'back_to_menu':
        balance = get_balance(user_id)
        message = f"🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n✨ Ваш баланс: {balance} раскладов"
        keyboard = [
            [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
            [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
            [InlineKeyboardButton("📺 Подписка (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    slots = get_saved_slots(user_id)
    occupied = len(slots)
    free = 3 - occupied
    
    message = f"🗄️ МОИ СОХРАНЁННЫЕ РАСКЛАДЫ 🗄️\n\n📦 Доступно ячеек для сохранения: {occupied}/3\n"
    if free > 0:
        message += f"✨ Свободно ячеек: {free}\n\n"
    else:
        message += "⚠️ Все ячейки заняты.\n\n"
    
    if not slots:
        message += "У вас пока нет сохранённых раскладов.\nСделайте расклад и нажмите «💾 Сохранить»!"
        keyboard = [[InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text=message, reply_markup=reply_markup)
        return
    
    keyboard = []
    for slot_num in sorted(slots.keys()):
        timestamp = slots[slot_num]
        keyboard.append([InlineKeyboardButton(f"📦 Ячейка #{slot_num} ({timestamp})", callback_data=f'view_slot_{slot_num}')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "📄 УСЛОВИЯ ОПЛАТЫ И СОГЛАСИЕ 📄\n"
        "\n💫 ВАЖНО: любая оплата в этом боте является ДОБРОВОЛЬНЫМ ДОНАТОМ.\n"
        "Расклады Таро предоставляются в развлекательных целях.\n"
        "Интерпретации карт не являются предсказанием будущего и не заменяют консультацию специалиста.\n"
        "\n✅ Нажимая «Оплатить», вы соглашаетесь с тем, что:\n"
        "• Оплата добровольная и необязательная.\n"
        "• Расклады носят развлекательный характер.\n"
        "• Вы совершаете платёж по собственной воле без принуждения.\n"
        "• Возврат средств не предусмотрен (добровольный донат).\n"
        "\n✨ Спасибо за поддержку проекта! 💫"
    )
    await update.message.reply_text(text=message)

def get_referral_count(user_id):
    conn = sqlite3.connect('tarot_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def main():
    init_db()
    if not TOKEN:
        print("❌ Токен не установлен")
        return
    print("✅ Бот запущен v5.0 (автоматическая криптооплата через NOWPayments)")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("terms", terms_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    main()