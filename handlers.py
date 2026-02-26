import re
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from utils import (
    add_user, get_balance, decrease_balance, get_saved_slots, save_reading,
    get_saved_reading, delete_saved_reading, create_payment, complete_payment,
    get_user_data, save_user_data, get_random_cards, format_reading,
    get_spread_options, get_referral_count, add_referral, mark_subscribed,
    check_subscribed, can_get_daily_card, save_daily_card, get_daily_card,
    format_daily_card, format_reading_intro, format_reading_cards, format_reading_advice,
    get_card_image_path, increment_reading_count, get_reading_count,
    create_sbp_payment, check_payment_status,
    get_all_users, get_total_users_count, get_total_readings_count
)

# ============================================================================
# 🔧 АДМИН-ПАНЕЛЬ - НАСТРОЙКИ
# ============================================================================

# ЗАМЕНИТЕ НА ВАШ USER_ID (можно узнать через @userinfobot в Telegram)
ADMIN_ID = 891543067  # ← Впишите сюда ваш числовой ID

# Имя пользователя админа для проверки
ADMIN_USERNAME = "jobphone_admin"

def is_admin(user_id, username=None):
    """Проверка, является ли пользователь админом"""
    if user_id == ADMIN_ID:
        return True
    if username and username.lower() == ADMIN_USERNAME.lower():
        return True
    return False

# ============================================================================
# 🔧 АДМИН-КОМАНДЫ
# ============================================================================

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📊 Статистика бота (только для админа)"""
    user = update.effective_user
    
    if not is_admin(user.id, user.username):
        await update.message.reply_text("❌ Доступ только для администратора")
        return
    
    total_users = get_total_users_count()
    total_readings = get_total_readings_count()
    
    message = (
        "📊 СТАТИСТИКА БОТА 📊\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🎴 Всего раскладов сделано: {total_readings}\n"
        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
    )
    
    await update.message.reply_text(message)

async def admin_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔍 Проверка баланса пользователя (только для админа)"""
    user = update.effective_user
    
    if not is_admin(user.id, user.username):
        await update.message.reply_text("❌ Доступ только для администратора")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Использование: /check <user_id>\n"
            "Пример: /check 123456789"
        )
        return
    
    try:
        check_user_id = int(context.args[0])
        balance = get_balance(check_user_id)
        user_data = get_user_data(check_user_id)
        reading_count = get_reading_count(check_user_id)
        referral_count = get_referral_count(check_user_id)
        
        message = (
            f"🔍 ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ 🔍\n\n"
            f"🆔 ID: {check_user_id}\n"
            f"👤 Имя: {user_data['name'] if user_data else 'Не указано'}\n"
            f"📅 Дата рождения: {user_data.get('birthdate', 'Не указана') if user_data else 'Не указана'}\n"
            f"⚖️ Баланс: {balance} раскладов\n"
            f"🎴 Всего раскладов: {reading_count}\n"
            f"👥 Приглашено друзей: {referral_count}\n"
        )
        
        await update.message.reply_text(message)
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат user_id (должно быть число)")

async def admin_addbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💰 Начислить баланс пользователю (только для админа)"""
    user = update.effective_user
    
    if not is_admin(user.id, user.username):
        await update.message.reply_text("❌ Доступ только для администратора")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Использование: /addbalance <user_id> <amount>\n"
            "Пример: /addbalance 123456789 5"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть больше 0")
            return
        
        from utils import increase_balance
        increase_balance(target_user_id, amount)
        
        message = (
            f"✅ Баланс успешно начислен!\n\n"
            f"👤 Пользователь: {target_user_id}\n"
            f"💰 Начислено: {amount} раскладов\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        await update.message.reply_text(message)
        
        # Уведомить пользователя
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"🎉 Вам начислено {amount} раскладов!\n\nСпасибо за оплату! 💫"
            )
        except:
            pass
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат (user_id и amount должны быть числами)")

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📋 Список всех пользователей (только для админа)"""
    user = update.effective_user
    
    if not is_admin(user.id, user.username):
        await update.message.reply_text("❌ Доступ только для администратора")
        return
    
    users = get_all_users()
    
    if not users:
        await update.message.reply_text("❌ Пользователи не найдены")
        return
    
    message = "📋 СПИСОК ПОЛЬЗОВАТЕЛЕЙ 📋\n\n"
    for i, (user_id, username, first_name, balance, created_at) in enumerate(users[:50], 1):
        message += f"{i}. {first_name} (@{username or 'no_username'}) - ID: {user_id} - Баланс: {balance}\n"
    
    if len(users) > 50:
        message += f"\n... и ещё {len(users) - 50} пользователей"
    
    await update.message.reply_text(message)

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📢 Рассылка всем пользователям (только для админа)"""
    user = update.effective_user
    
    if not is_admin(user.id, user.username):
        await update.message.reply_text("❌ Доступ только для администратора")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Использование: /broadcast <текст сообщения>\n"
            "Пример: /broadcast Привет! У нас акция!"
        )
        return
    
    message_text = " ".join(context.args)
    users = get_all_users()
    
    if not users:
        await update.message.reply_text("❌ Нет пользователей для рассылки")
        return
    
    success_count = 0
    fail_count = 0
    
    status_message = await update.message.reply_text(f"📢 Начало рассылки...\nВсего пользователей: {len(users)}")
    
    for user_id, username, first_name, balance, created_at in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 Сообщение от администратора:\n\n{message_text}"
            )
            success_count += 1
        except:
            fail_count += 1
        
        # Обновляем статус каждые 10 пользователей
        if success_count % 10 == 0:
            try:
                await context.bot.edit_message_text(
                    f"📢 Рассылка...\n✅ Отправлено: {success_count}\n❌ Ошибок: {fail_count}\n📊 Всего: {len(users)}",
                    chat_id=status_message.chat_id,
                    message_id=status_message.message_id
                )
            except:
                pass
    
    await context.bot.edit_message_text(
        f"✅ Рассылка завершена!\n\n✅ Успешно: {success_count}\n❌ Ошибок: {fail_count}\n📊 Всего: {len(users)}",
        chat_id=status_message.chat_id,
        message_id=status_message.message_id
    )

# ============================================================================
# ОСНОВНЫЕ ФУНКЦИИ БОТА (без изменений)
# ============================================================================

ASKING_NAME, ASKING_BIRTHDATE, READING_INTRO, READING_CARDS, READING_ADVICE = range(5)

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
                    except:
                        pass
        except:
            pass
    
    user_data = get_user_data(user.id)
    if not user_data or not user_data.get('name') or not user_data.get('birthdate'):
        await update.message.reply_text(
            "✨ Добро пожаловать в мир Таро!\n\n"
            "🔮 Для персонализированного гадания мне нужно узнать вас немного лучше.\n\n"
            "💫 Сначала напишите, как вас зовут: "
        )
        return ASKING_NAME
    
    balance = get_balance(user.id)
    message = f"🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n✨ {user_data['name']}, ваш баланс: {balance} раскладов"
    
    keyboard = [
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
        [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
        [InlineKeyboardButton("👤 Аккаунт", callback_data='account')],
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
    if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s]+$', name):
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
    if not re.match(r'^\d{2}.\d{2}.\d{4}$', birthdate):
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
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
        [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
        [InlineKeyboardButton("👤 Аккаунт", callback_data='account')],
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
        increment_reading_count(user_id)
        
        image_path = get_card_image_path(card_name)
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                await update.message.reply_photo(photo=photo, caption=reading)
        else:
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
        [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "❓ ПОМОЩЬ ❓\n"
        "\n✨ КАК ПОЛЬЗОВАТЬСЯ БОТОМ:\n"
        "• 🎴 Сделать расклад — подробный расклад из 3+ карт (списывается с баланса)\n"
        "• 🗄️ Мои расклады — сохраните результат в одну из 3 ячеек\n"
        "• 🌅 Карта дня — бесплатное гадание на сегодня (1 раз в день, в меню «Сделать расклад»)\n"
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
        "• СБП — автоматическое начисление ⚡\n"
        "• Банковская карта — ручная проверка скриншота ⏳\n"
        "• Подробнее об условиях: /terms"
    )
    keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name'):
        await update.message.reply_text("Сначала укажите имя и дату рождения через /start")
        return
    
    balance = get_balance(user_id)
    referral_count = get_referral_count(user_id)
    reading_count = get_reading_count(user_id)
    
    message = (
        f"👤 ВАШ АККАУНТ 👤\n"
        f"\n✨ Имя: {user_data['name']}\n"
        f"📅 Дата рождения: {user_data.get('birthdate', 'Не указана')}\n"
        f"\n⚖️ Баланс: {balance} раскладов\n"
        f"🎴 Всего раскладов сделано: {reading_count}\n"
        f"👥 Приглашено друзей: {referral_count}\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("📺 Подписка (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("🎁 Пригласить друга", callback_data='referral')],
        [InlineKeyboardButton("🔮 Главное меню", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

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
    
    context.user_data['current_reading'] = {
        'spread_id': spread_id,
        'cards': cards,
        'positions': spread_info['positions'],
        'user_name': user_data['name'],
        'balance_after': new_balance
    }
    
    intro_text = format_reading_intro(spread_id, user_data['name'])
    keyboard = [[InlineKeyboardButton("➡️ Далее", callback_data='reading_step_1')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=intro_text, reply_markup=reply_markup)
    return READING_INTRO

async def reading_step_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    reading_data = context.user_data.get('current_reading', {})
    
    if not reading_data:
        await query.edit_message_text(text="❌ Ошибка: данные расклада утеряны. Начните заново.")
        return
    
    cards = reading_data['cards']
    positions = reading_data['positions']
    
    for idx, card_data in enumerate(cards):
        card_name = card_data[0]
        interpretation = card_data[1]
        position_name = positions[idx] if idx < len(positions) else f"Карта {idx + 1}"
        
        card_caption = f"🎴 {position_name}\n"
        card_caption += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        card_caption += f"✨ КАРТА: {card_name}\n"
        card_caption += f"💫 ЗНАЧЕНИЕ: {interpretation['short']}\n"
        
        spread_id = reading_data['spread_id']
        if spread_id not in ['celtic_cross', 'past_present_future']:
            if spread_id == 'relationship':
                card_caption += f"\n❤️‍🔥 В ЛЮБВИ: {interpretation['love']}"
            elif spread_id == 'career':
                card_caption += f"\n💼 В КАРЬЕРЕ: {interpretation['career']}"
            else:
                card_caption += f"\n❤️‍🔥 В ЛЮБВИ: {interpretation['love']}"
                card_caption += f"\n💼 В КАРЬЕРЕ: {interpretation['career']}"
        
        image_path = get_card_image_path(card_name)
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                if idx == len(cards) - 1:
                    keyboard = [[InlineKeyboardButton("➡️ Далее к совету", callback_data='reading_step_2')]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo,
                        caption=card_caption,
                        reply_markup=reply_markup
                    )
                else:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo,
                        caption=card_caption
                    )
        else:
            if idx == len(cards) - 1:
                keyboard = [[InlineKeyboardButton("➡️ Далее к совету", callback_data='reading_step_2')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=card_caption,
                    reply_markup=reply_markup
                )
            else:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=card_caption
                )
    
    try:
        await query.message.delete()
    except:
        pass
    
    return READING_CARDS

async def reading_step_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    reading_data = context.user_data.get('current_reading', {})
    
    if not reading_data:
        await query.edit_message_text(text="❌ Ошибка: данные расклада утеряны. Начните заново.")
        return
    
    cards = reading_data['cards']
    spread_id = reading_data['spread_id']
    
    advice_text = format_reading_advice(cards, spread_id)
    
    if 'pending_readings' not in context.user_data:
        context.user_data['pending_readings'] = {}
    
    full_reading = format_reading_cards(
        cards,
        reading_data['user_name'],
        reading_data['positions'],
        spread_id
    ) + "\n\n" + advice_text
    
    context.user_data['pending_readings'][query.from_user.id] = (
        cards,
        full_reading
    )
    
    increment_reading_count(query.from_user.id)
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад к картам", callback_data='back_to_cards')],
        [InlineKeyboardButton("💾 Сохранить расклад", callback_data='save_last_reading')],
        [InlineKeyboardButton("🔄 Ещё один расклад", callback_data='do_tarot')],
        [InlineKeyboardButton(f"⚖️ Баланс: {reading_data['balance_after']}", callback_data='balance')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=advice_text,
        reply_markup=reply_markup
    )
    
    try:
        await query.message.delete()
    except:
        pass
    
    return READING_ADVICE

async def back_to_spread_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await choose_spread(update, context)
    return READING_INTRO

async def back_to_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await reading_step_1(update, context)
    return READING_CARDS

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'back_to_spread_choice':
        await back_to_spread_choice(update, context)
        return
    
    if query.data == 'back_to_cards':
        await back_to_cards(update, context)
        return
    
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
            increment_reading_count(user_id)
            
            image_path = get_card_image_path(card_name)
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo,
                        caption=reading
                    )
            else:
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
    
    if query.data == 'account':
        user_data = get_user_data(user_id)
        if not user_data or not user_data.get('name'):
            await query.message.reply_text("Сначала укажите имя и дату рождения через /start")
            return
        
        balance = get_balance(user_id)
        referral_count = get_referral_count(user_id)
        reading_count = get_reading_count(user_id)
        
        message = (
            f"👤 ВАШ АККАУНТ 👤\n"
            f"\n✨ Имя: {user_data['name']}\n"
            f"📅 Дата рождения: {user_data.get('birthdate', 'Не указана')}\n"
            f"\n⚖️ Баланс: {balance} раскладов\n"
            f"🎴 Всего раскладов сделано: {reading_count}\n"
            f"👥 Приглашено друзей: {referral_count}\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("📺 Подписка (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("🎁 Пригласить друга", callback_data='referral')],
            [InlineKeyboardButton("🔮 Главное меню", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
        return
    
    if query.data == 'referral':
        ref_link = f"https://t.me/cardnotlie_bot?start={user_id}"
        referral_count = get_referral_count(user_id)
        message = (
            f"🎁 РЕФЕРАЛЬНАЯ ПРОГРАММА 🎁\n\n"
            f"✨ Ваша реферальная ссылка:\n{ref_link}\n\n"
            f"📊 Приглашено друзей: {referral_count}\n"
            f"💫 За каждого друга — +1 бесплатный расклад!\n\n"
            f"📤 Просто отправьте ссылку друзьям или в соцсети!"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
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
        return
    
    if query.data.startswith('delete_slot_'):
        slot_num = int(query.data.split('_')[2])
        if delete_saved_reading(user_id, slot_num):
            message = f"✅ Расклад из ячейки #{slot_num} удалён."
        else:
            message = "❌ Ошибка удаления."
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
        return
    
    if query.data == 'saved_readings':
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
        return
    
    if query.data.startswith('view_slot_'):
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
        return
    
    if query.data == 'balance':
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
            [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
        return
    
    if query.data == 'buy_packs':
        message = (
            "💳 СПОСОБЫ ОПЛАТЫ 💳\n"
            "\nВыберите удобный способ:\n"
            "\n⚡ СБП — автоматическое начисление (рекомендуется)\n"
            "🏦 Банковская карта — ручная проверка скриншота ⏳\n"
        )
        keyboard = [
            [InlineKeyboardButton("⚡ СБП (автоматически)", callback_data='sbp_packs')],
            [InlineKeyboardButton("🏦 Банковская карта", callback_data='card_packs')],
            [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
        return
    
    if query.data == 'sbp_packs':
        message = (
            "💳 ПАКЕТЫ РАСКЛАДОВ (СБП) 💳\n"
            "\n✨ Выберите пакет со скидкой:\n"
            "\n🎴 1 расклад — 100 ₽\n"
            "🎴 3 расклада — 285 ₽ (-5%)\n"
            "🎴 7 раскладов — 630 ₽ (-10%)\n"
            "🎴 13 раскладов — 1 105 ₽ (-15%)\n"
        )
        keyboard = [
            [InlineKeyboardButton("1 расклад — 100₽", callback_data='sbp_buy_1')],
            [InlineKeyboardButton("3 расклада — 285₽ (-5%)", callback_data='sbp_buy_3')],
            [InlineKeyboardButton("7 раскладов — 630₽ (-10%)", callback_data='sbp_buy_7')],
            [InlineKeyboardButton("13 раскладов — 1 105₽ (-15%)", callback_data='sbp_buy_13')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='buy_packs')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
        return
    
    if query.data.startswith('sbp_buy_'):
        pack_size = int(query.data.split('_')[2])
        prices = {1: 100, 3: 285, 7: 630, 13: 1105}
        price = prices[pack_size]
        discounts = {1: "0%", 3: "5%", 7: "10%", 13: "15%"}
        discount = discounts[pack_size]
        
        payment_data = await create_sbp_payment(user_id, price, pack_size)
        
        if payment_data and payment_data.get('payment_url'):
            message = (
                f"💳 ОПЛАТА ПАКЕТА: {pack_size} раскладов 💳\n"
                f"\n💰 Стоимость: {price} ₽ (скидка {discount})\n"
                f"\n📱 ОПЛАТА ЧЕРЕЗ СБП:\n"
                f"1. Нажмите кнопку «📱 Оплатить через СБП» ниже\n"
                f"2. Отсканируйте QR-код в приложении вашего банка\n"
                f"3. Нажмите «🔄 Проверить статус» после оплаты\n"
                f"\n⏳ Платёж действителен 30 минут.\n"
                f"\nℹ️ Подробнее об условиях оплаты: /terms"
            )
            keyboard = [
                [InlineKeyboardButton("📱 Оплатить через СБП", url=payment_data['payment_url'])],
                [InlineKeyboardButton("🔄 Проверить статус оплаты", callback_data=f'check_payment_{payment_data["payment_id"]}')],
                [InlineKeyboardButton("⬅️ Назад к пакетам", callback_data='sbp_packs')],
                [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
            ]
        else:
            message = (
                f"💳 ОПЛАТА ПАКЕТА: {pack_size} раскладов 💳\n"
                f"\n💰 Стоимость: {price} ₽ (скидка {discount})\n"
                f"\n⚠️ Временно недоступно. Попробуйте оплату картой.\n"
            )
            keyboard = [
                [InlineKeyboardButton("🏦 Банковская карта", callback_data='card_packs')],
                [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
        return
    
    if query.data.startswith('check_payment_'):
        payment_id = query.data.replace('check_payment_', '')
        
        await query.answer("⏳ Проверяем статус оплаты...")
        
        payment_status = await check_payment_status(payment_id)
        
        if payment_status:
            if payment_status['status'] == 'PAID':
                message = "✅ Оплата подтверждена! Расклады начислены на ваш баланс.\n\n🎴 Приятного пользования!"
                keyboard = [[InlineKeyboardButton("🔮 Главное меню", callback_data='back_to_menu')]]
            elif payment_status['status'] == 'PENDING':
                message = "⏳ Оплата ещё не подтверждена.\n\nПожалуйста, завершите оплату в приложении банка и нажмите «Проверить статус» снова."
                keyboard = [
                    [InlineKeyboardButton("🔄 Проверить статус", callback_data=f'check_payment_{payment_id}')],
                    [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
                ]
            else:
                message = "❌ Платёж не найден или отклонён.\n\nПопробуйте создать новый платёж."
                keyboard = [[InlineKeyboardButton("🔮 Главное меню", callback_data='back_to_menu')]]
        else:
            message = "⏳ Ожидание оплаты...\n\nНажмите «Проверить статус» через 1-2 минуты после оплаты."
            keyboard = [
                [InlineKeyboardButton("🔄 Проверить статус", callback_data=f'check_payment_{payment_id}')],
                [InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
        return
    
    if query.data == 'card_packs':
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
        return
    
    if query.data.startswith('buy_'):
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
            f"▫️ Номер карты: 2200300564643334 \n"
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
        return
    
    if query.data == 'terms' or query.data == 'terms_button':
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
        return
    
    if query.data == 'subscribe':
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
        return
    
    if query.data == 'confirm_subscribe':
        subscribed_db = check_subscribed(user_id)
        
        if subscribed_db:
            message = "✅ Вы уже получили бонус за подписку!"
        else:
            try:
                channel_id = -1003865254581
                chat_member = await context.bot.get_chat_member(
                    chat_id=channel_id,
                    user_id=user_id
                )
                if chat_member.status in ["member", "administrator", "creator"]:
                    mark_subscribed(user_id)
                    message = "🎉 Ура! Вы подписались на канал!\n✨ Бонус +3 бесплатных расклада начислен на ваш счёт!"
                else:
                    message = "❌ Вы не подписаны на канал.\nПожалуйста, подпишитесь и нажмите кнопку снова."
            except Exception as e:
                print(f"Ошибка проверки подписки: {e}")
                message = "❌ Не удалось проверить подписку. Попробуйте позже."
        
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
        return
    
    if query.data == 'help':
        message = (
            "❓ ПОМОЩЬ ❓\n"
            "\n✨ КАК ПОЛЬЗОВАТЬСЯ БОТОМ:\n"
            "• 🎴 Сделать расклад — подробный расклад из 3+ карт (списывается с баланса)\n"
            "• 🗄️ Мои расклады — сохраните результат в одну из 3 ячеек\n"
            "• 🌅 Карта дня — бесплатное гадание на сегодня (1 раз в день, в меню «Сделать расклад»)\n"
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
            "• СБП — автоматическое начисление ⚡\n"
            "• Банковская карта — ручная проверка скриншота ⏳\n"
            "• Подробнее об условиях: /terms"
        )
        keyboard = [[InlineKeyboardButton("⬅️ Меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
        return
    
    if query.data == 'back_to_menu':
        user_data = get_user_data(user_id)
        if not user_data or not user_data.get('name'):
            await query.message.reply_text("Напишите своё имя:")
            return
        
        balance = get_balance(user_id)
        message = f"🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n✨ {user_data['name']}, ваш баланс: {balance} раскладов"
        keyboard = [
            [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
            [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
            [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
            [InlineKeyboardButton("👤 Аккаунт", callback_data='account')],
            [InlineKeyboardButton("❓ Помощь", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
        return

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
    
    message = "🎴 ВЫБЕРИТЕ ТИП РАСКЛАДА 🎴\n\n"
    keyboard = []
    
    keyboard.append([InlineKeyboardButton("🌅 Карта дня (бесплатно)", callback_data='daily_card')])
    
    for spread_id, spread_info in spreads.items():
        if spread_id != 'daily':
            keyboard.append([InlineKeyboardButton(spread_info['name'], callback_data=f'spread_{spread_id}')])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=message, reply_markup=reply_markup)

start_handler = ConversationHandler(
    entry_points=[CommandHandler("start", _start)],
    states={
        ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASKING_BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_birthdate)],
        READING_INTRO: [CallbackQueryHandler(reading_step_1, pattern='^reading_step_1$')],
        READING_CARDS: [CallbackQueryHandler(reading_step_2, pattern='^reading_step_2$')],
        READING_ADVICE: [CallbackQueryHandler(button_handler)]
    },
    fallbacks=[CommandHandler("start", _start)],
    allow_reentry=True,
    per_message=False
)

async def reading_step_1_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await reading_step_1(update, context)

async def reading_step_2_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await reading_step_2(update, context)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name'):
        await update.message.reply_text("Сначала укажите имя и дату рождения через /start")
        return
    
    balance = get_balance(user_id)
    message = f"🔮 ДОБРО ПОЖАЛОВАТЬ В МИР ТАРО! 🔮\n✨ {user_data['name']}, ваш баланс: {balance} раскладов"
    
    keyboard = [
        [InlineKeyboardButton("🎴 Сделать расклад", callback_data='do_tarot')],
        [InlineKeyboardButton("🗄️ Мои расклады", callback_data='saved_readings')],
        [InlineKeyboardButton(f"⚖️ Баланс: {balance}", callback_data='balance')],
        [InlineKeyboardButton("👤 Аккаунт", callback_data='account')],
        [InlineKeyboardButton("❓ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def account_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await account_command(update, context)