import re
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from flask import request

from utils import (
    add_user, get_balance, decrease_balance, get_saved_slots, save_reading,
    get_saved_reading, delete_saved_reading, create_payment, complete_payment,
    get_user_data, save_user_data, get_random_cards, format_reading,
    get_spread_options, get_referral_count, add_referral, mark_subscribed,
    check_subscribed, can_get_daily_card, save_daily_card, get_daily_card,
    format_daily_card  # ← ЭТА СТРОКА ДОЛЖНА БЫТЬ
)

ASKING_NAME, ASKING_BIRTHDATE = range(2)

async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)
    
    if context.args:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user.id:
                if add_referral(referrer_id, user.id):
                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 Отлично! Ваш друг {user.first_name} присоединился!\nВы получили +1 расклад к балансу!"
                        )
                    except: pass
        except: pass
    
    user_data = get_user_data(user.id)
    if not user_data or not user_data.get('name') or not user_data.get('birthdate'):
        await update.message.reply_text(
            "✨ Добро пожаловать в мир Таро!\n\n"
            "🔮 Для персонализированного гадания мне нужно узнать вас немного лучше.\n\n"
            "💫 Сначала напишите, как вас зовут:"
        )
        return ASKING_NAME
    
    balance = get_balance(user.id)
    message = f"🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n✨ {user_data['name']}, ваш баланс: {balance} раскладов"
    
    keyboard = [
        [InlineKeyboardButton("🌅 Карта дня (бесплатно)", callback_data='daily_card')],
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
        [InlineKeyboardButton("📺 Подписка (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)
    return ConversationHandler.END

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("❌ Имя должно быть не менее 2 символов. Попробуйте ещё раз:")
        return ASKING_NAME
    
    if not re.match(r'^[а-яА-Яa-zA-Z\s]+$', name):
        await update.message.reply_text("❌ Имя может содержать только буквы и пробелы. Попробуйте ещё раз:")
        return ASKING_NAME
    
    context.user_data['temp_name'] = name
    await update.message.reply_text(
        f"✨ Приятно познакомиться, {name}!\n\n"
        "💫 Теперь напишите вашу дату рождения в формате:\n"
        "📅 ДД.ММ.ГГГГ (например: 15.08.1990)"
    )
    return ASKING_BIRTHDATE

async def ask_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    birthdate = update.message.text.strip()
    
    if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', birthdate):
        await update.message.reply_text(
            "❌ Неверный формат даты.\n"
            "📅 Пожалуйста, напишите в формате ДД.ММ.ГГГГ\n"
            "Пример: 15.08.1990"
        )
        return ASKING_BIRTHDATE
    
    try:
        day, month, year = map(int, birthdate.split('.'))
        birth_date = datetime(year, month, day)
        today = datetime.today()
        
        if birth_date > today or year < 1900:
            await update.message.reply_text(
                "❌ Проверьте дату: год должен быть после 1900, а дата — не в будущем.\n"
                "📅 Пример правильной даты: 15.08.1990"
            )
            return ASKING_BIRTHDATE
            
    except ValueError:
        await update.message.reply_text(
            "❌ Неверная дата. Убедитесь, что дата существует.\n"
            "📅 Пример: 15.08.1990 (а не 31.02.1990)"
        )
        return ASKING_BIRTHDATE
    
    user_id = update.effective_user.id
    name = context.user_data.get('temp_name', 'Аноним')
    save_user_data(user_id, name, birthdate)
    
    if 'temp_name' in context.user_data:
        del context.user_data['temp_name']
    
    balance = get_balance(user_id)
    await update.message.reply_text(
        f"✅ Отлично, {name}! Данные сохранены.\n\n"
        f"✨ Ваш баланс: {balance} раскладов\n"
        f"🎴 Готовы к первому гаданию?"
    )
    
    keyboard = [
        [InlineKeyboardButton("🌅 Карта дня (бесплатно)", callback_data='daily_card')],
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
        [InlineKeyboardButton("📺 Подписка (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔮 Выберите действие:", reply_markup=reply_markup)
    return ConversationHandler.END

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

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if not user_data or not user_data.get('name'):
        await update.message.reply_text("Сначала укажите имя и дату рождения через /start")
        return
    
    if can_get_daily_card(user_id):
        card = get_random_cards(1)[0]
        card_name, interpretation = card
        reading = format_daily_card(card_name, interpretation, user_data['name'])
        save_daily_card(user_id, card_name, reading)
        
        await update.message.reply_text(text=reading)
        await update.message.reply_text(
            text="🌅 Карта дня получена! Возвращайтесь завтра за новой картой.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
                [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
            ])
        )
    else:
        await update.message.reply_text(
            text="🌅 Вы уже получили карту дня сегодня!\nВозвращайтесь завтра за новой картой ☀️",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
            ])
        )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if not user_data or not user_data.get('name'):
        await update.message.reply_text("Сначала укажите имя и дату рождения через /start")
        return
    
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
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "❓ ПОМОЩЬ ❓\n"
        "\n✨ КАК ПОЛЬЗОВАТЬСЯ БОТОМ:\n"
        "• 🌅 Карта дня — бесплатное гадание на сегодня (1 раз в день)\n"
        "• 🎴 Сделать расклад — подробный расклад из 3+ карт (списывается с баланса)\n"
        "• 💾 Сохранить расклад — сохраните результат в одну из 3 ячеек\n"
        "\n🗄️ СОХРАНЕНИЕ РАСКЛАДОВ:\n"
        "• У вас есть 3 ячейки для сохранения раскладов.\n"
        "• Расклады НЕ сохраняются автоматически — только по вашему выбору.\n"
        "• Если все ячейки заняты — сначала удалите старый расклад.\n"
        "\n⚖️ БАЛАНС:\n"
        "• При регистрации: 1 бесплатный расклад.\n"
        "• 🌅 Карта дня — всегда бесплатно, 1 раз в день.\n"
        "• За друга: +1 расклад.\n"
        "• За подписку: +3 расклада.\n"
        "• Покупка пакетов со скидкой до 15%.\n"
        "\n💳 ОПЛАТА:\n"
        "• Банковская карта — ручная проверка скриншота ⏳\n"
        "• Криптовалюта — в разработке 🔜\n"
        "• Подробнее об условиях: /terms"
    )
    keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

start_handler = ConversationHandler(
    entry_points=[CommandHandler("start", _start)],
    states={
        ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASKING_BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_birthdate)],
        READING_INTRO: [CallbackQueryHandler(reading_step_1, pattern='^reading_step_1$')],
        READING_CARDS: [CallbackQueryHandler(reading_step_2, pattern='^reading_step_2$')],
        READING_ADVICE: [CallbackQueryHandler(button_handler)]  # Возвращаемся к основному обработчику
    },
    fallbacks=[CommandHandler("start", _start)],
    allow_reentry=True
)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'daily_card':
        user_data = get_user_data(user_id)
        if not user_data or not user_data.get('name'):
            await query.message.reply_text("Сначала укажите имя и дату рождения через /start")
            return
        
        if can_get_daily_card(user_id):
            card = get_random_cards(1)[0]
            card_name, interpretation = card
            reading = format_daily_card(card_name, interpretation, user_data['name'])
            save_daily_card(user_id, card_name, reading)
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=reading
            )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="🌅 Карта дня получена! Возвращайтесь завтра за новой картой.\n\n💫 Хотите сделать подробный расклад? Нажмите «🎴 Сделать расклад»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
                    [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
                ])
            )
        else:
            await query.edit_message_text(
                text="🌅 Вы уже получили карту дня сегодня!\nВозвращайтесь завтра за новой картой ☀️",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
                ])
            )
        return
    
    if query.data.startswith('spread_'):
        await process_spread_selection(update, context)
        return
    
    if query.data == 'do_tarot':
        await choose_spread(update, context)
        return
    
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name') or not user_data.get('birthdate'):
        await query.message.reply_text(
            "✨ Для начала гадания мне нужны ваши данные:\n"
            "1. Имя\n"
            "2. Дата рождения (ДД.ММ.ГГГГ)\n\n"
            "Напишите своё имя:"
        )
        return
    
    if query.data == 'save_last_reading':
        if 'pending_readings' in context.user_data and user_id in context.user_data.get('pending_readings', {}):
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
            "\n🏦 Банковская карта — требуется ручная проверка скриншота ⏳\n"
            "💎 Криптовалюта — в разработке 🔜"
        )
        keyboard = [
            [InlineKeyboardButton("🏦 Банковская карта", callback_data='card_packs')],
            [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
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
            "• 🌅 Карта дня — бесплатное гадание на сегодня (1 раз в день)\n"
            "• 🎴 Сделать расклад — подробный расклад из 3+ карт (списывается с баланса)\n"
            "• 💾 Сохранить расклад — сохраните результат в одну из 3 ячеек\n"
            "\n🗄️ СОХРАНЕНИЕ РАСКЛАДОВ:\n"
            "• У вас есть 3 ячейки для сохранения раскладов.\n"
            "• Расклады НЕ сохраняются автоматически — только по вашему выбору.\n"
            "• Если все ячейки заняты — сначала удалите старый расклад.\n"
            "\n⚖️ БАЛАНС:\n"
            "• При регистрации: 1 бесплатный расклад.\n"
            "• 🌅 Карта дня — всегда бесплатно, 1 раз в день.\n"
            "• За друга: +1 расклад.\n"
            "• За подписку: +3 расклада.\n"
            "• Покупка пакетов со скидкой до 15%.\n"
            "\n💳 ОПЛАТА:\n"
            "• Банковская карта — ручная проверка скриншота ⏳\n"
            "• Криптовалюта — в разработке 🔜\n"
            "• Подробнее об условиях: /terms"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'back_to_menu':
        user_data = get_user_data(user_id)
        if not user_data or not user_data.get('name'):
            await query.message.reply_text("Напишите своё имя:")
            return
        
        balance = get_balance(user_id)
        message = f"🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n✨ {user_data['name']}, ваш баланс: {balance} раскладов"
        keyboard = [
            [InlineKeyboardButton("🌅 Карта дня (бесплатно)", callback_data='daily_card')],
            [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
            [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
            [InlineKeyboardButton("📺 Подписка (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)

async def choose_spread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name'):
        await query.message.reply_text("Сначала укажите имя и дату рождения через /start")
        return
    
    balance = get_balance(user_id)
    if balance <= 0:
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
        return
    
    spreads = get_spread_options()
    spreads.pop('daily', None)
    
    message = "🎴 ВЫБЕРИТЕ ТИП РАСКЛАДА 🎴\n\n"
    keyboard = []
    
    for spread_id, spread_info in spreads.items():
        keyboard.append([InlineKeyboardButton(spread_info['name'], callback_data=f'spread_{spread_id}')])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=message, reply_markup=reply_markup)

# ... (начало файла без изменений) ...

# Новые состояния для многоэтапного расклада
READING_INTRO, READING_CARDS, READING_ADVICE = range(3, 6)

async def process_spread_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    spread_id = query.data.replace('spread_', '')
    
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name'):
        await query.message.reply_text("Сначала укажите имя и дату рождения через /start")
        return
    
    balance = get_balance(user_id)
    if balance <= 0:
        await query.edit_message_text(text="❌ У вас недостаточно раскладов. Пополните баланс!")
        return
    
    # ✅ Списываем 1 расклад ДО начала расклада
    if not decrease_balance(user_id, 1):
        await query.edit_message_text(text="❌ Ошибка при списании расклада. Попробуйте позже.")
        return
    
    new_balance = get_balance(user_id)
    spreads = get_spread_options()
    
    if spread_id not in spreads:
        await query.edit_message_text(text=f"❌ Неверный тип расклада: '{spread_id}'")
        return
    
    spread_info = spreads[spread_id]
    cards = get_random_cards(spread_info['cards_count'])
    
    # ✅ Сохраняем данные расклада в контексте
    context.user_data['current_reading'] = {
        'spread_id': spread_id,
        'cards': cards,
        'positions': spread_info['positions'],
        'user_name': user_data['name'],
        'balance_after': new_balance
    }
    
    # ✅ Этап 1: Вводная часть с описанием
    intro_text = format_reading_intro(spread_id, user_data['name'])
    keyboard = [[InlineKeyboardButton("➡️ Далее", callback_data='reading_step_1')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=intro_text, reply_markup=reply_markup)
    return READING_INTRO

async def reading_step_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Этап 2: Показ карт и значений"""
    query = update.callback_query
    await query.answer()
    
    reading_data = context.user_data.get('current_reading', {})
    if not reading_data:
        await query.edit_message_text(text="❌ Ошибка: данные расклада утеряны. Начните заново.")
        return
    
    cards_text = format_reading_cards(
        reading_data['cards'],
        reading_data['user_name'],
        reading_data['positions'],
        reading_data['spread_id']
    )
    
    keyboard = [[InlineKeyboardButton("➡️ Далее", callback_data='reading_step_2')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=cards_text, reply_markup=reply_markup)
    return READING_CARDS

async def reading_step_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Этап 3: Персональный совет + предупреждение"""
    query = update.callback_query
    await query.answer()
    
    reading_data = context.user_data.get('current_reading', {})
    if not reading_data:
        await query.edit_message_text(text="❌ Ошибка: данные расклада утеряны. Начните заново.")
        return
    
    advice_text = format_reading_advice(
        reading_data['cards'],
        reading_data['spread_id']
    )
    
    # Сохраняем расклад для возможного сохранения
    if 'pending_readings' not in context.user_data:
        context.user_data['pending_readings'] = {}
    
    # Формируем полный расклад для сохранения
    full_reading = (
        format_reading_cards(
            reading_data['cards'],
            reading_data['user_name'],
            reading_data['positions'],
            reading_data['spread_id']
        ) + "\n\n" + advice_text
    )
    
    context.user_data['pending_readings'][query.from_user.id] = (
        reading_data['cards'],
        full_reading
    )
    
    keyboard = [
        [InlineKeyboardButton("💾 Сохранить расклад", callback_data='save_last_reading')],
        [InlineKeyboardButton("🔄 Ещё один расклад", callback_data='do_tarot')],
        [InlineKeyboardButton(f"⚖️ Баланс: {reading_data['balance_after']}", callback_data='balance')],
        [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем совет как НОВОЕ сообщение (чтобы не редактировать длинный текст)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=advice_text,
        reply_markup=reply_markup
    )
    
    # Удаляем предыдущее сообщение с картами
    try:
        await query.message.delete()
    except:
        pass
    
    return READING_ADVICE

