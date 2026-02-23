import re
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from flask import request

from utils import (
    add_user, get_balance, decrease_balance, get_saved_slots, save_reading,
    get_saved_reading, delete_saved_reading, create_payment, complete_payment,
    get_user_data, save_user_data, get_random_cards, format_reading,
    get_spread_options, get_referral_count, add_referral, mark_subscribed,
    check_subscribed, can_get_daily_card, save_daily_card, get_daily_card,
    format_daily_card, format_reading_intro, format_reading_cards, format_reading_advice
)

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
                            text=f"?? Ð ÑÐ¡âÐ Â»Ð ÑÐ¡â¡Ð ÐÐ Ñ! Ð âÐ Â°Ð¡â¬ Ð ÒÐ¡ÐÐ¡ÑÐ Ñ {user.first_name} Ð ÑÐ¡ÐÐ ÑÐ¡ÐÐ ÑÐ ÂµÐ ÒÐ ÑÐ ÐÐ ÑÐ Â»Ð¡ÐÐ¡Ð!\nÐ âÐ¡â¹ Ð ÑÐ ÑÐ Â»Ð¡ÑÐ¡â¡Ð ÑÐ Â»Ð Ñ +1 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð Ñ Ð Â±Ð Â°Ð Â»Ð Â°Ð ÐÐ¡ÐÐ¡Ñ!"
                        )
                    except: pass
        except: pass
    
    user_data = get_user_data(user.id)
    if not user_data or not user_data.get('name') or not user_data.get('birthdate'):
        await update.message.reply_text(
            "? Ð âÐ ÑÐ Â±Ð¡ÐÐ Ñ Ð ÑÐ ÑÐ Â¶Ð Â°Ð Â»Ð ÑÐ ÐÐ Â°Ð¡âÐ¡Ð Ð Ð Ð ÑÐ ÑÐ¡Ð Ð ÑÐ Â°Ð¡ÐÐ Ñ!\n\n"
            "?? Ð âÐ Â»Ð¡Ð Ð ÑÐ ÂµÐ¡ÐÐ¡ÐÐ ÑÐ ÐÐ Â°Ð Â»Ð ÑÐ Â·Ð ÑÐ¡ÐÐ ÑÐ ÐÐ Â°Ð ÐÐ ÐÐ ÑÐ ÑÐ Ñ Ð ÑÐ Â°Ð ÒÐ Â°Ð ÐÐ ÑÐ¡Ð Ð ÑÐ ÐÐ Âµ Ð ÐÐ¡ÑÐ Â¶Ð ÐÐ Ñ Ð¡ÑÐ Â·Ð ÐÐ Â°Ð¡âÐ¡Ð Ð ÐÐ Â°Ð¡Ð Ð ÐÐ ÂµÐ ÑÐ ÐÐ ÑÐ ÑÐ Ñ Ð Â»Ð¡ÑÐ¡â¡Ð¡â¬Ð Âµ.\n\n"
            "?? Ð ÐÐ ÐÐ Â°Ð¡â¡Ð Â°Ð Â»Ð Â° Ð ÐÐ Â°Ð ÑÐ ÑÐ¡â¬Ð ÑÐ¡âÐ Âµ, Ð ÑÐ Â°Ð Ñ Ð ÐÐ Â°Ð¡Ð Ð Â·Ð ÑÐ ÐÐ¡ÑÐ¡â:"
        )
        return ASKING_NAME
    
    balance = get_balance(user.id)
    message = f"?? Ð âÐ ÑÐ âÐ Â Ð Ñ Ð ÑÐ ÑÐ âÐ ÑÐ âºÐ ÑÐ âÐ ÑÐ ÑÐ Â¬ Ð â Ð ÑÐ ÂÐ Â  Ð ÑÐ ÑÐ Â Ð Ñ! ??\n? {user_data['name']}, Ð ÐÐ Â°Ð¡â¬ Ð Â±Ð Â°Ð Â»Ð Â°Ð ÐÐ¡Ð: {balance} Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð"
    
    keyboard = [
        [InlineKeyboardButton("?? Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â° Ð ÒÐ ÐÐ¡Ð (Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ Â»Ð Â°Ð¡âÐ ÐÐ Ñ)", callback_data='daily_card')],
        [InlineKeyboardButton("?? Ð ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò", callback_data='do_tarot')],
        [InlineKeyboardButton(f"?? Ð âÐ Â°Ð Â»Ð Â°Ð ÐÐ¡Ð: {balance}", callback_data='balance')],
        [InlineKeyboardButton("?? Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ ÑÐ Â° (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("??? Ð ÑÐ ÑÐ Ñ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹", callback_data='saved_readings')],
        [InlineKeyboardButton("? Ð ÑÐ ÑÐ ÑÐ ÑÐ¡â°Ð¡Ð", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)
    return ConversationHandler.END

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("? Ð ÂÐ ÑÐ¡Ð Ð ÒÐ ÑÐ Â»Ð Â¶Ð ÐÐ Ñ Ð Â±Ð¡â¹Ð¡âÐ¡Ð Ð ÐÐ Âµ Ð ÑÐ ÂµÐ ÐÐ ÂµÐ Âµ 2 Ð¡ÐÐ ÑÐ ÑÐ ÐÐ ÑÐ Â»Ð ÑÐ Ð. Ð ÑÐ ÑÐ ÑÐ¡ÐÐ ÑÐ Â±Ð¡ÑÐ âÐ¡âÐ Âµ Ð ÂµÐ¡â°Ð¡â Ð¡ÐÐ Â°Ð Â·:")
        return ASKING_NAME
    
    if not re.match(r'^[a-zA-ZÐ Â°-Ð¡ÐÐ Ñ-Ð ÐÐ¡âÐ Ð\s]+$', name):
        await update.message.reply_text("? Ð ÂÐ ÑÐ¡Ð Ð ÑÐ ÑÐ Â¶Ð ÂµÐ¡â Ð¡ÐÐ ÑÐ ÒÐ ÂµÐ¡ÐÐ Â¶Ð Â°Ð¡âÐ¡Ð Ð¡âÐ ÑÐ Â»Ð¡ÐÐ ÑÐ Ñ Ð Â±Ð¡ÑÐ ÑÐ ÐÐ¡â¹ Ð Ñ Ð ÑÐ¡ÐÐ ÑÐ Â±Ð ÂµÐ Â»Ð¡â¹. Ð ÑÐ ÑÐ ÑÐ¡ÐÐ ÑÐ Â±Ð¡ÑÐ âÐ¡âÐ Âµ Ð ÂµÐ¡â°Ð¡â Ð¡ÐÐ Â°Ð Â·:")
        return ASKING_NAME
    
    context.user_data['temp_name'] = name
    await update.message.reply_text(
        f"? Ð ÑÐ¡ÐÐ ÑÐ¡ÐÐ¡âÐ ÐÐ Ñ Ð ÑÐ ÑÐ Â·Ð ÐÐ Â°Ð ÑÐ ÑÐ ÑÐ ÑÐ¡âÐ¡ÐÐ¡ÐÐ¡Ð, {name}!\n\n"
        "?? Ð ÑÐ ÂµÐ ÑÐ ÂµÐ¡ÐÐ¡Ð Ð ÐÐ Â°Ð ÑÐ ÑÐ¡â¬Ð ÑÐ¡âÐ Âµ Ð ÐÐ Â°Ð¡â¬Ð¡Ñ Ð ÒÐ Â°Ð¡âÐ¡Ñ Ð¡ÐÐ ÑÐ Â¶Ð ÒÐ ÂµÐ ÐÐ ÑÐ¡Ð Ð Ð Ð¡âÐ ÑÐ¡ÐÐ ÑÐ Â°Ð¡âÐ Âµ:\n"
        "?? Ð âÐ â.Ð ÑÐ Ñ.Ð âÐ âÐ âÐ â (Ð ÐÐ Â°Ð ÑÐ¡ÐÐ ÑÐ ÑÐ ÂµÐ¡Ð: 15.08.1990)"
    )
    return ASKING_BIRTHDATE

async def ask_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    birthdate = update.message.text.strip()
    
    if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', birthdate):
        await update.message.reply_text(
            "? Ð ÑÐ ÂµÐ ÐÐ ÂµÐ¡ÐÐ ÐÐ¡â¹Ð â Ð¡âÐ ÑÐ¡ÐÐ ÑÐ Â°Ð¡â Ð ÒÐ Â°Ð¡âÐ¡â¹.\n"
            "?? Ð ÑÐ ÑÐ Â¶Ð Â°Ð Â»Ð¡ÑÐ âÐ¡ÐÐ¡âÐ Â°, Ð ÐÐ Â°Ð ÑÐ ÑÐ¡â¬Ð ÑÐ¡âÐ Âµ Ð Ð Ð¡âÐ ÑÐ¡ÐÐ ÑÐ Â°Ð¡âÐ Âµ Ð âÐ â.Ð ÑÐ Ñ.Ð âÐ âÐ âÐ â\n"
            "Ð ÑÐ¡ÐÐ ÑÐ ÑÐ ÂµÐ¡Ð: 15.08.1990"
        )
        return ASKING_BIRTHDATE
    
    try:
        day, month, year = map(int, birthdate.split('.'))
        birth_date = datetime(year, month, day)
        today = datetime.today()
        
        if birth_date > today or year < 1900:
            await update.message.reply_text(
                "? Ð ÑÐ¡ÐÐ ÑÐ ÐÐ ÂµÐ¡ÐÐ¡ÐÐ¡âÐ Âµ Ð ÒÐ Â°Ð¡âÐ¡Ñ: Ð ÑÐ ÑÐ Ò Ð ÒÐ ÑÐ Â»Ð Â¶Ð ÂµÐ Ð Ð Â±Ð¡â¹Ð¡âÐ¡Ð Ð ÑÐ ÑÐ¡ÐÐ Â»Ð Âµ 1900, Ð Â° Ð ÒÐ Â°Ð¡âÐ Â° Ð²Ðâ Ð ÐÐ Âµ Ð Ð Ð Â±Ð¡ÑÐ ÒÐ¡ÑÐ¡â°Ð ÂµÐ Ñ.\n"
                "?? Ð ÑÐ¡ÐÐ ÑÐ ÑÐ ÂµÐ¡Ð Ð ÑÐ¡ÐÐ Â°Ð ÐÐ ÑÐ Â»Ð¡ÐÐ ÐÐ ÑÐ â Ð ÒÐ Â°Ð¡âÐ¡â¹: 15.08.1990"
            )
            return ASKING_BIRTHDATE
            
    except ValueError:
        await update.message.reply_text(
            "? Ð ÑÐ ÂµÐ ÐÐ ÂµÐ¡ÐÐ ÐÐ Â°Ð¡Ð Ð ÒÐ Â°Ð¡âÐ Â°. Ð ÐÐ Â±Ð ÂµÐ ÒÐ ÑÐ¡âÐ ÂµÐ¡ÐÐ¡Ð, Ð¡â¡Ð¡âÐ Ñ Ð ÒÐ Â°Ð¡âÐ Â° Ð¡ÐÐ¡ÑÐ¡â°Ð ÂµÐ¡ÐÐ¡âÐ ÐÐ¡ÑÐ ÂµÐ¡â.\n"
            "?? Ð ÑÐ¡ÐÐ ÑÐ ÑÐ ÂµÐ¡Ð: 15.08.1990 (Ð Â° Ð ÐÐ Âµ 31.02.1990)"
        )
        return ASKING_BIRTHDATE
    
    user_id = update.effective_user.id
    name = context.user_data.get('temp_name', 'Ð ÑÐ ÐÐ ÑÐ ÐÐ ÑÐ Ñ')
    save_user_data(user_id, name, birthdate)
    
    if 'temp_name' in context.user_data:
        del context.user_data['temp_name']
    
    balance = get_balance(user_id)
    await update.message.reply_text(
        f"? Ð ÑÐ¡âÐ Â»Ð ÑÐ¡â¡Ð ÐÐ Ñ, {name}! Ð âÐ Â°Ð ÐÐ ÐÐ¡â¹Ð Âµ Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÂµÐ ÐÐ¡â¹.\n\n"
        f"? Ð âÐ Â°Ð¡â¬ Ð Â±Ð Â°Ð Â»Ð Â°Ð ÐÐ¡Ð: {balance} Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð\n"
        f"?? Ð âÐ ÑÐ¡âÐ ÑÐ ÐÐ¡â¹ Ð Ñ Ð ÑÐ ÂµÐ¡ÐÐ ÐÐ ÑÐ ÑÐ¡Ñ Ð ÑÐ Â°Ð ÒÐ Â°Ð ÐÐ ÑÐ¡Ð?"
    )
    
    keyboard = [
        [InlineKeyboardButton("?? Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â° Ð ÒÐ ÐÐ¡Ð (Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ Â»Ð Â°Ð¡âÐ ÐÐ Ñ)", callback_data='daily_card')],
        [InlineKeyboardButton("?? Ð ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò", callback_data='do_tarot')],
        [InlineKeyboardButton(f"?? Ð âÐ Â°Ð Â»Ð Â°Ð ÐÐ¡Ð: {balance}", callback_data='balance')],
        [InlineKeyboardButton("?? Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ ÑÐ Â° (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("??? Ð ÑÐ ÑÐ Ñ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹", callback_data='saved_readings')],
        [InlineKeyboardButton("? Ð ÑÐ ÑÐ ÑÐ ÑÐ¡â°Ð¡Ð", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("?? Ð âÐ¡â¹Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ¡âÐ Âµ Ð ÒÐ ÂµÐ âÐ¡ÐÐ¡âÐ ÐÐ ÑÐ Âµ:", reply_markup=reply_markup)
    return ConversationHandler.END

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    slots = get_saved_slots(user_id)
    occupied = len(slots)
    free = 3 - occupied
    
    message = f"??? Ð ÑÐ ÑÐ Â Ð ÐÐ ÑÐ ÒÐ Â Ð ÑÐ ÑÐ ÐÐ ÑÐ ÑÐ Â«Ð â¢ Ð Â Ð ÑÐ ÐÐ ÑÐ âºÐ ÑÐ âÐ Â« ???\n\n?? Ð âÐ ÑÐ¡ÐÐ¡âÐ¡ÑÐ ÑÐ ÐÐ Ñ Ð¡ÐÐ¡â¡Ð ÂµÐ ÂµÐ Ñ Ð ÒÐ Â»Ð¡Ð Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÂµÐ ÐÐ ÑÐ¡Ð: {occupied}/3\n"
    if free > 0:
        message += f"? Ð ÐÐ ÐÐ ÑÐ Â±Ð ÑÐ ÒÐ ÐÐ Ñ Ð¡ÐÐ¡â¡Ð ÂµÐ ÂµÐ Ñ: {free}\n\n"
    else:
        message += "?? Ð âÐ¡ÐÐ Âµ Ð¡ÐÐ¡â¡Ð ÂµÐ âÐ ÑÐ Ñ Ð Â·Ð Â°Ð ÐÐ¡ÐÐ¡âÐ¡â¹.\n\n"
    
    if not slots:
        message += "Ð Ð Ð ÐÐ Â°Ð¡Ð Ð ÑÐ ÑÐ ÑÐ Â° Ð ÐÐ ÂµÐ¡â Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ¡âÐ ÐÐ ÐÐ¡â¹Ð¡â¦ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð.\nÐ ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð âÐ¡âÐ Âµ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð Ñ Ð ÐÐ Â°Ð Â¶Ð ÑÐ ÑÐ¡âÐ Âµ ÐÂ«?? Ð ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÑÐ¡âÐ¡ÐÐÂ»!"
        keyboard = [[InlineKeyboardButton("?? Ð ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò", callback_data='do_tarot')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text=message, reply_markup=reply_markup)
        return
    
    keyboard = []
    for slot_num in sorted(slots.keys()):
        timestamp = slots[slot_num]
        keyboard.append([InlineKeyboardButton(f"?? Ð ÐÐ¡â¡Ð ÂµÐ âÐ ÑÐ Â° #{slot_num} ({timestamp})", callback_data=f'view_slot_{slot_num}')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "?? Ð ÐÐ ÐÐ âºÐ ÑÐ âÐ ÂÐ Ð Ð ÑÐ ÑÐ âºÐ ÑÐ ÑÐ Â« Ð Â Ð ÐÐ ÑÐ âÐ âºÐ ÑÐ ÐÐ ÂÐ â¢ ??\n"
        "\n?? Ð âÐ ÑÐ âÐ ÑÐ Ñ: Ð Â»Ð¡ÐÐ Â±Ð Â°Ð¡Ð Ð ÑÐ ÑÐ Â»Ð Â°Ð¡âÐ Â° Ð Ð Ð¡ÐÐ¡âÐ ÑÐ Ñ Ð Â±Ð ÑÐ¡âÐ Âµ Ð¡ÐÐ ÐÐ Â»Ð¡ÐÐ ÂµÐ¡âÐ¡ÐÐ¡Ð Ð âÐ ÑÐ âÐ Â Ð ÑÐ âÐ ÑÐ âºÐ Â¬Ð ÑÐ Â«Ð Ñ Ð âÐ ÑÐ ÑÐ ÑÐ ÑÐ ÑÐ Ñ.\n"
        "Ð Â Ð Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹ Ð ÑÐ Â°Ð¡ÐÐ Ñ Ð ÑÐ¡ÐÐ ÂµÐ ÒÐ ÑÐ¡ÐÐ¡âÐ Â°Ð ÐÐ Â»Ð¡ÐÐ¡ÐÐ¡âÐ¡ÐÐ¡Ð Ð Ð Ð¡ÐÐ Â°Ð Â·Ð ÐÐ Â»Ð ÂµÐ ÑÐ Â°Ð¡âÐ ÂµÐ Â»Ð¡ÐÐ ÐÐ¡â¹Ð¡â¦ Ð¡â Ð ÂµÐ Â»Ð¡ÐÐ¡â¦.\n"
        "Ð ÂÐ ÐÐ¡âÐ ÂµÐ¡ÐÐ ÑÐ¡ÐÐ ÂµÐ¡âÐ Â°Ð¡â Ð ÑÐ Ñ Ð ÑÐ Â°Ð¡ÐÐ¡â Ð ÐÐ Âµ Ð¡ÐÐ ÐÐ Â»Ð¡ÐÐ¡ÐÐ¡âÐ¡ÐÐ¡Ð Ð ÑÐ¡ÐÐ ÂµÐ ÒÐ¡ÐÐ ÑÐ Â°Ð Â·Ð Â°Ð ÐÐ ÑÐ ÂµÐ Ñ Ð Â±Ð¡ÑÐ ÒÐ¡ÑÐ¡â°Ð ÂµÐ ÑÐ Ñ Ð Ñ Ð ÐÐ Âµ Ð Â·Ð Â°Ð ÑÐ ÂµÐ ÐÐ¡ÐÐ¡ÐÐ¡â Ð ÑÐ ÑÐ ÐÐ¡ÐÐ¡ÑÐ Â»Ð¡ÐÐ¡âÐ Â°Ð¡â Ð ÑÐ¡Ð Ð¡ÐÐ ÑÐ ÂµÐ¡â Ð ÑÐ Â°Ð Â»Ð ÑÐ¡ÐÐ¡âÐ Â°.\n"
        "\n? Ð ÑÐ Â°Ð Â¶Ð ÑÐ ÑÐ Â°Ð¡Ð ÐÂ«Ð ÑÐ ÑÐ Â»Ð Â°Ð¡âÐ ÑÐ¡âÐ¡ÐÐÂ», Ð ÐÐ¡â¹ Ð¡ÐÐ ÑÐ ÑÐ Â»Ð Â°Ð¡â¬Ð Â°Ð ÂµÐ¡âÐ ÂµÐ¡ÐÐ¡Ð Ð¡Ð Ð¡âÐ ÂµÐ Ñ, Ð¡â¡Ð¡âÐ Ñ:\n"
        "Ð²ÐÑ Ð ÑÐ ÑÐ Â»Ð Â°Ð¡âÐ Â° Ð ÒÐ ÑÐ Â±Ð¡ÐÐ ÑÐ ÐÐ ÑÐ Â»Ð¡ÐÐ ÐÐ Â°Ð¡Ð Ð Ñ Ð ÐÐ ÂµÐ ÑÐ Â±Ð¡ÐÐ Â·Ð Â°Ð¡âÐ ÂµÐ Â»Ð¡ÐÐ ÐÐ Â°Ð¡Ð.\n"
        "Ð²ÐÑ Ð Â Ð Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹ Ð ÐÐ ÑÐ¡ÐÐ¡ÐÐ¡â Ð¡ÐÐ Â°Ð Â·Ð ÐÐ Â»Ð ÂµÐ ÑÐ Â°Ð¡âÐ ÂµÐ Â»Ð¡ÐÐ ÐÐ¡â¹Ð â Ð¡â¦Ð Â°Ð¡ÐÐ Â°Ð ÑÐ¡âÐ ÂµÐ¡Ð.\n"
        "Ð²ÐÑ Ð âÐ¡â¹ Ð¡ÐÐ ÑÐ ÐÐ ÂµÐ¡ÐÐ¡â¬Ð Â°Ð ÂµÐ¡âÐ Âµ Ð ÑÐ Â»Ð Â°Ð¡âÐ¡âÐ Â¶ Ð ÑÐ Ñ Ð¡ÐÐ ÑÐ Â±Ð¡ÐÐ¡âÐ ÐÐ ÂµÐ ÐÐ ÐÐ ÑÐ â Ð ÐÐ ÑÐ Â»Ð Âµ Ð Â±Ð ÂµÐ Â· Ð ÑÐ¡ÐÐ ÑÐ ÐÐ¡ÑÐ Â¶Ð ÒÐ ÂµÐ ÐÐ ÑÐ¡Ð.\n"
        "Ð²ÐÑ Ð âÐ ÑÐ Â·Ð ÐÐ¡ÐÐ Â°Ð¡â Ð¡ÐÐ¡ÐÐ ÂµÐ ÒÐ¡ÐÐ¡âÐ Ð Ð ÐÐ Âµ Ð ÑÐ¡ÐÐ ÂµÐ ÒÐ¡ÑÐ¡ÐÐ ÑÐ ÑÐ¡âÐ¡ÐÐ ÂµÐ Ð (Ð ÒÐ ÑÐ Â±Ð¡ÐÐ ÑÐ ÐÐ ÑÐ Â»Ð¡ÐÐ ÐÐ¡â¹Ð â Ð ÒÐ ÑÐ ÐÐ Â°Ð¡â).\n"
        "\n? Ð ÐÐ ÑÐ Â°Ð¡ÐÐ ÑÐ Â±Ð Ñ Ð Â·Ð Â° Ð ÑÐ ÑÐ ÒÐ ÒÐ ÂµÐ¡ÐÐ Â¶Ð ÑÐ¡Ñ Ð ÑÐ¡ÐÐ ÑÐ ÂµÐ ÑÐ¡âÐ Â°! ??"
    )
    await update.message.reply_text(text=message)

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if not user_data or not user_data.get('name'):
        await update.message.reply_text("Ð ÐÐ ÐÐ Â°Ð¡â¡Ð Â°Ð Â»Ð Â° Ð¡ÑÐ ÑÐ Â°Ð Â¶Ð ÑÐ¡âÐ Âµ Ð ÑÐ ÑÐ¡Ð Ð Ñ Ð ÒÐ Â°Ð¡âÐ¡Ñ Ð¡ÐÐ ÑÐ Â¶Ð ÒÐ ÂµÐ ÐÐ ÑÐ¡Ð Ð¡â¡Ð ÂµÐ¡ÐÐ ÂµÐ Â· /start")
        return
    
    if can_get_daily_card(user_id):
        card = get_random_cards(1)[0]
        card_name, interpretation = card
        reading = format_daily_card(card_name, interpretation, user_data['name'])
        save_daily_card(user_id, card_name, reading)
        
        await update.message.reply_text(text=reading)
        await update.message.reply_text(
            text="?? Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â° Ð ÒÐ ÐÐ¡Ð Ð ÑÐ ÑÐ Â»Ð¡ÑÐ¡â¡Ð ÂµÐ ÐÐ Â°! Ð âÐ ÑÐ Â·Ð ÐÐ¡ÐÐ Â°Ð¡â°Ð Â°Ð âÐ¡âÐ ÂµÐ¡ÐÐ¡Ð Ð Â·Ð Â°Ð ÐÐ¡âÐ¡ÐÐ Â° Ð Â·Ð Â° Ð ÐÐ ÑÐ ÐÐ ÑÐ â Ð ÑÐ Â°Ð¡ÐÐ¡âÐ ÑÐ â.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("?? Ð ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò", callback_data='do_tarot')],
                [InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]
            ])
        )
    else:
        await update.message.reply_text(
            text="?? Ð âÐ¡â¹ Ð¡ÑÐ Â¶Ð Âµ Ð ÑÐ ÑÐ Â»Ð¡ÑÐ¡â¡Ð ÑÐ Â»Ð Ñ Ð ÑÐ Â°Ð¡ÐÐ¡âÐ¡Ñ Ð ÒÐ ÐÐ¡Ð Ð¡ÐÐ ÂµÐ ÑÐ ÑÐ ÒÐ ÐÐ¡Ð!\nÐ âÐ ÑÐ Â·Ð ÐÐ¡ÐÐ Â°Ð¡â°Ð Â°Ð âÐ¡âÐ ÂµÐ¡ÐÐ¡Ð Ð Â·Ð Â°Ð ÐÐ¡âÐ¡ÐÐ Â° Ð Â·Ð Â° Ð ÐÐ ÑÐ ÐÐ ÑÐ â Ð ÑÐ Â°Ð¡ÐÐ¡âÐ ÑÐ â ??",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]
            ])
        )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if not user_data or not user_data.get('name'):
        await update.message.reply_text("Ð ÐÐ ÐÐ Â°Ð¡â¡Ð Â°Ð Â»Ð Â° Ð¡ÑÐ ÑÐ Â°Ð Â¶Ð ÑÐ¡âÐ Âµ Ð ÑÐ ÑÐ¡Ð Ð Ñ Ð ÒÐ Â°Ð¡âÐ¡Ñ Ð¡ÐÐ ÑÐ Â¶Ð ÒÐ ÂµÐ ÐÐ ÑÐ¡Ð Ð¡â¡Ð ÂµÐ¡ÐÐ ÂµÐ Â· /start")
        return
    
    balance = get_balance(user_id)
    message = (
        f"?? Ð âÐ ÑÐ Ð Ð ÑÐ â¢Ð ÑÐ ÐÐ Â©Ð ÂÐ â¢ Ð âÐ ÑÐ âºÐ ÑÐ ÑÐ Ð ??\n"
        f"\n?? Ð âÐ ÑÐ¡ÐÐ¡âÐ¡ÑÐ ÑÐ ÐÐ Ñ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð: {balance}\n"
        f"\n? Ð ÑÐ Â°Ð Ñ Ð ÑÐ ÑÐ Â»Ð¡ÑÐ¡â¡Ð ÑÐ¡âÐ¡Ð Ð Â±Ð ÑÐ Â»Ð¡ÐÐ¡â¬Ð Âµ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð:\n"
        f"Ð²ÐÑ Ð ÑÐ¡ÐÐ ÑÐ ÑÐ Â»Ð Â°Ð¡ÐÐ ÑÐ¡âÐ Âµ Ð ÒÐ¡ÐÐ¡ÑÐ ÑÐ Â° Ð²Ðâ +1 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò ??\n"
        f"Ð²ÐÑ Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡â¬Ð ÑÐ¡âÐ ÂµÐ¡ÐÐ¡Ð Ð ÐÐ Â° Ð ÑÐ Â°Ð ÐÐ Â°Ð Â» Ð²Ðâ +3 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â° ??\n"
        f"Ð²ÐÑ Ð ÑÐ¡ÑÐ ÑÐ ÑÐ¡âÐ Âµ Ð ÑÐ Â°Ð ÑÐ ÂµÐ¡â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð Ð¡ÐÐ Ñ Ð¡ÐÐ ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ â ??"
    )
    keyboard = [
        [InlineKeyboardButton("?? Ð ÑÐ¡ÑÐ ÑÐ ÑÐ¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹", callback_data='buy_packs')],
        [InlineKeyboardButton("?? Ð ÑÐ¡ÐÐ ÑÐ ÑÐ Â»Ð Â°Ð¡ÐÐ ÑÐ¡âÐ¡Ð Ð ÒÐ¡ÐÐ¡ÑÐ ÑÐ Â°", callback_data='referral')],
        [InlineKeyboardButton("?? Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ Â°Ð¡âÐ¡ÐÐ¡ÐÐ¡Ð (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "? Ð ÑÐ ÑÐ ÑÐ ÑÐ Â©Ð Â¬ ?\n"
        "\n? Ð ÑÐ ÑÐ Ñ Ð ÑÐ ÑÐ âºÐ Â¬Ð âÐ ÑÐ âÐ ÑÐ ÑÐ Â¬Ð ÐÐ Ð Ð âÐ ÑÐ ÑÐ ÑÐ Ñ:\n"
        "Ð²ÐÑ ?? Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â° Ð ÒÐ ÐÐ¡Ð Ð²Ðâ Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ Â»Ð Â°Ð¡âÐ ÐÐ ÑÐ Âµ Ð ÑÐ Â°Ð ÒÐ Â°Ð ÐÐ ÑÐ Âµ Ð ÐÐ Â° Ð¡ÐÐ ÂµÐ ÑÐ ÑÐ ÒÐ ÐÐ¡Ð (1 Ð¡ÐÐ Â°Ð Â· Ð Ð Ð ÒÐ ÂµÐ ÐÐ¡Ð)\n"
        "Ð²ÐÑ ?? Ð ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð²Ðâ Ð ÑÐ ÑÐ ÒÐ¡ÐÐ ÑÐ Â±Ð ÐÐ¡â¹Ð â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð ÑÐ Â· 3+ Ð ÑÐ Â°Ð¡ÐÐ¡â (Ð¡ÐÐ ÑÐ ÑÐ¡ÐÐ¡â¹Ð ÐÐ Â°Ð ÂµÐ¡âÐ¡ÐÐ¡Ð Ð¡Ð Ð Â±Ð Â°Ð Â»Ð Â°Ð ÐÐ¡ÐÐ Â°)\n"
        "Ð²ÐÑ ?? Ð ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÑÐ¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð²Ðâ Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÑÐ¡âÐ Âµ Ð¡ÐÐ ÂµÐ Â·Ð¡ÑÐ Â»Ð¡ÐÐ¡âÐ Â°Ð¡â Ð Ð Ð ÑÐ ÒÐ ÐÐ¡Ñ Ð ÑÐ Â· 3 Ð¡ÐÐ¡â¡Ð ÂµÐ ÂµÐ Ñ\n"
        "\n??? Ð ÐÐ ÑÐ ÒÐ Â Ð ÑÐ ÑÐ â¢Ð ÑÐ ÂÐ â¢ Ð Â Ð ÑÐ ÐÐ ÑÐ âºÐ ÑÐ âÐ ÑÐ â:\n"
        "Ð²ÐÑ Ð Ð Ð ÐÐ Â°Ð¡Ð Ð ÂµÐ¡ÐÐ¡âÐ¡Ð 3 Ð¡ÐÐ¡â¡Ð ÂµÐ âÐ ÑÐ Ñ Ð ÒÐ Â»Ð¡Ð Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÂµÐ ÐÐ ÑÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð.\n"
        "Ð²ÐÑ Ð Â Ð Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹ Ð ÑÐ â¢ Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ¡ÐÐ¡ÐÐ¡âÐ¡ÐÐ¡Ð Ð Â°Ð ÐÐ¡âÐ ÑÐ ÑÐ Â°Ð¡âÐ ÑÐ¡â¡Ð ÂµÐ¡ÐÐ ÑÐ Ñ Ð²Ðâ Ð¡âÐ ÑÐ Â»Ð¡ÐÐ ÑÐ Ñ Ð ÑÐ Ñ Ð ÐÐ Â°Ð¡â¬Ð ÂµÐ ÑÐ¡Ñ Ð ÐÐ¡â¹Ð Â±Ð ÑÐ¡ÐÐ¡Ñ.\n"
        "Ð²ÐÑ Ð â¢Ð¡ÐÐ Â»Ð Ñ Ð ÐÐ¡ÐÐ Âµ Ð¡ÐÐ¡â¡Ð ÂµÐ âÐ ÑÐ Ñ Ð Â·Ð Â°Ð ÐÐ¡ÐÐ¡âÐ¡â¹ Ð²Ðâ Ð¡ÐÐ ÐÐ Â°Ð¡â¡Ð Â°Ð Â»Ð Â° Ð¡ÑÐ ÒÐ Â°Ð Â»Ð ÑÐ¡âÐ Âµ Ð¡ÐÐ¡âÐ Â°Ð¡ÐÐ¡â¹Ð â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò.\n"
        "\n?? Ð âÐ ÑÐ âºÐ ÑÐ ÑÐ Ð:\n"
        "Ð²ÐÑ Ð ÑÐ¡ÐÐ Ñ Ð¡ÐÐ ÂµÐ ÑÐ ÑÐ¡ÐÐ¡âÐ¡ÐÐ Â°Ð¡â Ð ÑÐ Ñ: 1 Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ Â»Ð Â°Ð¡âÐ ÐÐ¡â¹Ð â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò.\n"
        "Ð²ÐÑ ?? Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â° Ð ÒÐ ÐÐ¡Ð Ð²Ðâ Ð ÐÐ¡ÐÐ ÂµÐ ÑÐ ÒÐ Â° Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ Â»Ð Â°Ð¡âÐ ÐÐ Ñ, 1 Ð¡ÐÐ Â°Ð Â· Ð Ð Ð ÒÐ ÂµÐ ÐÐ¡Ð.\n"
        "Ð²ÐÑ Ð âÐ Â° Ð ÒÐ¡ÐÐ¡ÑÐ ÑÐ Â°: +1 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò.\n"
        "Ð²ÐÑ Ð âÐ Â° Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ ÑÐ¡Ñ: +3 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â°.\n"
        "Ð²ÐÑ Ð ÑÐ ÑÐ ÑÐ¡ÑÐ ÑÐ ÑÐ Â° Ð ÑÐ Â°Ð ÑÐ ÂµÐ¡âÐ ÑÐ Ð Ð¡ÐÐ Ñ Ð¡ÐÐ ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ â Ð ÒÐ Ñ 15%.\n"
        "\n?? Ð ÑÐ ÑÐ âºÐ ÑÐ ÑÐ Ñ:\n"
        "Ð²ÐÑ Ð âÐ Â°Ð ÐÐ ÑÐ ÑÐ ÐÐ¡ÐÐ ÑÐ Â°Ð¡Ð Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â° Ð²Ðâ Ð¡ÐÐ¡ÑÐ¡â¡Ð ÐÐ Â°Ð¡Ð Ð ÑÐ¡ÐÐ ÑÐ ÐÐ ÂµÐ¡ÐÐ ÑÐ Â° Ð¡ÐÐ ÑÐ¡ÐÐ ÑÐ ÐÐ¡â¬Ð ÑÐ¡âÐ Â° ?\n"
        "Ð²ÐÑ Ð ÑÐ¡ÐÐ ÑÐ ÑÐ¡âÐ ÑÐ ÐÐ Â°Ð Â»Ð¡ÐÐ¡âÐ Â° Ð²Ðâ Ð Ð Ð¡ÐÐ Â°Ð Â·Ð¡ÐÐ Â°Ð Â±Ð ÑÐ¡âÐ ÑÐ Âµ ??\n"
        "Ð²ÐÑ Ð ÑÐ ÑÐ ÒÐ¡ÐÐ ÑÐ Â±Ð ÐÐ ÂµÐ Âµ Ð ÑÐ Â± Ð¡ÑÐ¡ÐÐ Â»Ð ÑÐ ÐÐ ÑÐ¡ÐÐ¡â¦: /terms"
    )
    keyboard = [[InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def process_spread_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    spread_id = query.data.replace('spread_', '')
    
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name'):
        await query.message.reply_text("Ð ÐÐ ÐÐ Â°Ð¡â¡Ð Â°Ð Â»Ð Â° Ð¡ÑÐ ÑÐ Â°Ð Â¶Ð ÑÐ¡âÐ Âµ Ð ÑÐ ÑÐ¡Ð Ð Ñ Ð ÒÐ Â°Ð¡âÐ¡Ñ Ð¡ÐÐ ÑÐ Â¶Ð ÒÐ ÂµÐ ÐÐ ÑÐ¡Ð Ð¡â¡Ð ÂµÐ¡ÐÐ ÂµÐ Â· /start")
        return
    
    balance = get_balance(user_id)
    if balance <= 0:
        await query.edit_message_text(text="? Ð Ð Ð ÐÐ Â°Ð¡Ð Ð ÐÐ ÂµÐ ÒÐ ÑÐ¡ÐÐ¡âÐ Â°Ð¡âÐ ÑÐ¡â¡Ð ÐÐ Ñ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð. Ð ÑÐ ÑÐ ÑÐ ÑÐ Â»Ð ÐÐ ÑÐ¡âÐ Âµ Ð Â±Ð Â°Ð Â»Ð Â°Ð ÐÐ¡Ð!")
        return
    
    if not decrease_balance(user_id, 1):
        await query.edit_message_text(text="? Ð ÑÐ¡â¬Ð ÑÐ Â±Ð ÑÐ Â° Ð ÑÐ¡ÐÐ Ñ Ð¡ÐÐ ÑÐ ÑÐ¡ÐÐ Â°Ð ÐÐ ÑÐ Ñ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â°. Ð ÑÐ ÑÐ ÑÐ¡ÐÐ ÑÐ Â±Ð¡ÑÐ âÐ¡âÐ Âµ Ð ÑÐ ÑÐ Â·Ð Â¶Ð Âµ.")
        return
    
    new_balance = get_balance(user_id)
    spreads = get_spread_options()
    
    if spread_id not in spreads:
        await query.edit_message_text(text=f"? Ð ÑÐ ÂµÐ ÐÐ ÂµÐ¡ÐÐ ÐÐ¡â¹Ð â Ð¡âÐ ÑÐ Ñ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â°: '{spread_id}'")
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
    keyboard = [[InlineKeyboardButton("?? Ð âÐ Â°Ð Â»Ð ÂµÐ Âµ", callback_data='reading_step_1')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=intro_text, reply_markup=reply_markup)
    return READING_INTRO

async def reading_step_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    reading_data = context.user_data.get('current_reading', {})
    if not reading_data:
        await query.edit_message_text(text="? Ð ÑÐ¡â¬Ð ÑÐ Â±Ð ÑÐ Â°: Ð ÒÐ Â°Ð ÐÐ ÐÐ¡â¹Ð Âµ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â° Ð¡ÑÐ¡âÐ ÂµÐ¡ÐÐ¡ÐÐ ÐÐ¡â¹. Ð ÑÐ Â°Ð¡â¡Ð ÐÐ ÑÐ¡âÐ Âµ Ð Â·Ð Â°Ð ÐÐ ÑÐ ÐÐ Ñ.")
        return
    
    cards_text = format_reading_cards(
        reading_data['cards'],
        reading_data['user_name'],
        reading_data['positions'],
        reading_data['spread_id']
    )
    
    keyboard = [
        [InlineKeyboardButton("?? Ð ÑÐ Â°Ð Â·Ð Â°Ð Ò", callback_data='back_to_spread_choice')],
        [InlineKeyboardButton("?? Ð âÐ Â°Ð Â»Ð ÂµÐ Âµ", callback_data='reading_step_2')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=cards_text, reply_markup=reply_markup)
    return READING_CARDS

async def reading_step_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    reading_data = context.user_data.get('current_reading', {})
    if not reading_data:
        await query.edit_message_text(text="? Ð ÑÐ¡â¬Ð ÑÐ Â±Ð ÑÐ Â°: Ð ÒÐ Â°Ð ÐÐ ÐÐ¡â¹Ð Âµ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â° Ð¡ÑÐ¡âÐ ÂµÐ¡ÐÐ¡ÐÐ ÐÐ¡â¹. Ð ÑÐ Â°Ð¡â¡Ð ÐÐ ÑÐ¡âÐ Âµ Ð Â·Ð Â°Ð ÐÐ ÑÐ ÐÐ Ñ.")
        return
    
    advice_text = format_reading_advice(
        reading_data['cards'],
        reading_data['spread_id']
    )
    
    if 'pending_readings' not in context.user_data:
        context.user_data['pending_readings'] = {}
    
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
        [InlineKeyboardButton("?? Ð ÑÐ Â°Ð Â·Ð Â°Ð Ò Ð Ñ Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â°Ð Ñ", callback_data='back_to_cards')],
        [InlineKeyboardButton("?? Ð ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÑÐ¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò", callback_data='save_last_reading')],
        [InlineKeyboardButton("?? Ð â¢Ð¡â°Ð¡â Ð ÑÐ ÒÐ ÑÐ Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò", callback_data='do_tarot')],
        [InlineKeyboardButton(f"?? Ð âÐ Â°Ð Â»Ð Â°Ð ÐÐ¡Ð: {reading_data['balance_after']}", callback_data='balance')],
        [InlineKeyboardButton("?? Ð âÐ Â»Ð Â°Ð ÐÐ ÐÐ ÑÐ Âµ Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]
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
            await query.message.reply_text("Ð ÐÐ ÐÐ Â°Ð¡â¡Ð Â°Ð Â»Ð Â° Ð¡ÑÐ ÑÐ Â°Ð Â¶Ð ÑÐ¡âÐ Âµ Ð ÑÐ ÑÐ¡Ð Ð Ñ Ð ÒÐ Â°Ð¡âÐ¡Ñ Ð¡ÐÐ ÑÐ Â¶Ð ÒÐ ÂµÐ ÐÐ ÑÐ¡Ð Ð¡â¡Ð ÂµÐ¡ÐÐ ÂµÐ Â· /start")
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
                text="?? Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â° Ð ÒÐ ÐÐ¡Ð Ð ÑÐ ÑÐ Â»Ð¡ÑÐ¡â¡Ð ÂµÐ ÐÐ Â°! Ð âÐ ÑÐ Â·Ð ÐÐ¡ÐÐ Â°Ð¡â°Ð Â°Ð âÐ¡âÐ ÂµÐ¡ÐÐ¡Ð Ð Â·Ð Â°Ð ÐÐ¡âÐ¡ÐÐ Â° Ð Â·Ð Â° Ð ÐÐ ÑÐ ÐÐ ÑÐ â Ð ÑÐ Â°Ð¡ÐÐ¡âÐ ÑÐ â.\n\n?? Ð ÒÐ ÑÐ¡âÐ ÑÐ¡âÐ Âµ Ð¡ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð¡âÐ¡Ð Ð ÑÐ ÑÐ ÒÐ¡ÐÐ ÑÐ Â±Ð ÐÐ¡â¹Ð â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò? Ð ÑÐ Â°Ð Â¶Ð ÑÐ ÑÐ¡âÐ Âµ ÐÂ«?? Ð ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐÂ»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("?? Ð ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò", callback_data='do_tarot')],
                    [InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]
                ])
            )
        else:
            await query.edit_message_text(
                text="?? Ð âÐ¡â¹ Ð¡ÑÐ Â¶Ð Âµ Ð ÑÐ ÑÐ Â»Ð¡ÑÐ¡â¡Ð ÑÐ Â»Ð Ñ Ð ÑÐ Â°Ð¡ÐÐ¡âÐ¡Ñ Ð ÒÐ ÐÐ¡Ð Ð¡ÐÐ ÂµÐ ÑÐ ÑÐ ÒÐ ÐÐ¡Ð!\nÐ âÐ ÑÐ Â·Ð ÐÐ¡ÐÐ Â°Ð¡â°Ð Â°Ð âÐ¡âÐ ÂµÐ¡ÐÐ¡Ð Ð Â·Ð Â°Ð ÐÐ¡âÐ¡ÐÐ Â° Ð Â·Ð Â° Ð ÐÐ ÑÐ ÐÐ ÑÐ â Ð ÑÐ Â°Ð¡ÐÐ¡âÐ ÑÐ â ??",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]
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
            "? Ð âÐ Â»Ð¡Ð Ð ÐÐ Â°Ð¡â¡Ð Â°Ð Â»Ð Â° Ð ÑÐ Â°Ð ÒÐ Â°Ð ÐÐ ÑÐ¡Ð Ð ÑÐ ÐÐ Âµ Ð ÐÐ¡ÑÐ Â¶Ð ÐÐ¡â¹ Ð ÐÐ Â°Ð¡â¬Ð Ñ Ð ÒÐ Â°Ð ÐÐ ÐÐ¡â¹Ð Âµ:\n"
            "1. Ð ÂÐ ÑÐ¡Ð\n"
            "2. Ð âÐ Â°Ð¡âÐ Â° Ð¡ÐÐ ÑÐ Â¶Ð ÒÐ ÂµÐ ÐÐ ÑÐ¡Ð (Ð âÐ â.Ð ÑÐ Ñ.Ð âÐ âÐ âÐ â)\n\n"
            "Ð ÑÐ Â°Ð ÑÐ ÑÐ¡â¬Ð ÑÐ¡âÐ Âµ Ð¡ÐÐ ÐÐ ÑÐ¡â Ð ÑÐ ÑÐ¡Ð:"
        )
        return
    
    if query.data == 'save_last_reading':
        if 'pending_readings' in context.user_data and user_id in context.user_data.get('pending_readings', {}):
            cards, reading_text = context.user_data['pending_readings'][user_id]
            slots = get_saved_slots(user_id)
            free_slots = [i for i in range(1, 4) if i not in slots]
            
            if free_slots:
                slot = save_reading(user_id, cards, reading_text, free_slots[0])
                message = f"? Ð Â Ð Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ¡âÐ Ð Ð Ð Ð¡ÐÐ¡â¡Ð ÂµÐ âÐ ÑÐ¡Ñ #{slot}!"
                keyboard = [[InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text=message, reply_markup=reply_markup)
                del context.user_data['pending_readings'][user_id]
            else:
                message = "?? Ð âÐ¡ÐÐ Âµ 3 Ð¡ÐÐ¡â¡Ð ÂµÐ âÐ ÑÐ Ñ Ð Â·Ð Â°Ð ÐÐ¡ÐÐ¡âÐ¡â¹. Ð ÐÐ ÐÐ Â°Ð¡â¡Ð Â°Ð Â»Ð Â° Ð¡ÑÐ ÒÐ Â°Ð Â»Ð ÑÐ¡âÐ Âµ Ð¡ÐÐ¡âÐ Â°Ð¡ÐÐ¡â¹Ð â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò:"
                keyboard = []
                for slot_num, timestamp in slots.items():
                    keyboard.append([InlineKeyboardButton(f"? Ð ÐÐ¡â¡Ð ÂµÐ âÐ ÑÐ Â° #{slot_num} ({timestamp})", callback_data=f'delete_slot_{slot_num}')])
                keyboard.append([InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text=message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="? Ð ÑÐ ÂµÐ¡â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â° Ð ÒÐ Â»Ð¡Ð Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÂµÐ ÐÐ ÑÐ¡Ð. Ð ÐÐ ÐÐ Â°Ð¡â¡Ð Â°Ð Â»Ð Â° Ð¡ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð âÐ¡âÐ Âµ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò!")
    
    elif query.data.startswith('delete_slot_'):
        slot_num = int(query.data.split('_')[2])
        if delete_saved_reading(user_id, slot_num):
            message = f"? Ð Â Ð Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð ÑÐ Â· Ð¡ÐÐ¡â¡Ð ÂµÐ âÐ ÑÐ Ñ #{slot_num} Ð¡ÑÐ ÒÐ Â°Ð Â»Ð¡âÐ Ð."
        else:
            message = "? Ð ÑÐ¡â¬Ð ÑÐ Â±Ð ÑÐ Â° Ð¡ÑÐ ÒÐ Â°Ð Â»Ð ÂµÐ ÐÐ ÑÐ¡Ð."
        keyboard = [[InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'saved_readings':
        slots = get_saved_slots(user_id)
        occupied = len(slots)
        free = 3 - occupied
        
        message = f"??? Ð ÑÐ ÑÐ Â Ð ÐÐ ÑÐ ÒÐ Â Ð ÑÐ ÑÐ ÐÐ ÑÐ ÑÐ Â«Ð â¢ Ð Â Ð ÑÐ ÐÐ ÑÐ âºÐ ÑÐ âÐ Â« ???\n?? Ð âÐ ÑÐ¡ÐÐ¡âÐ¡ÑÐ ÑÐ ÐÐ Ñ Ð¡ÐÐ¡â¡Ð ÂµÐ ÂµÐ Ñ Ð ÒÐ Â»Ð¡Ð Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÂµÐ ÐÐ ÑÐ¡Ð: {occupied}/3\n"
        if free > 0:
            message += f"? Ð ÐÐ ÐÐ ÑÐ Â±Ð ÑÐ ÒÐ ÐÐ Ñ Ð¡ÐÐ¡â¡Ð ÂµÐ ÂµÐ Ñ: {free}\n\n"
        else:
            message += "?? Ð âÐ¡ÐÐ Âµ Ð¡ÐÐ¡â¡Ð ÂµÐ âÐ ÑÐ Ñ Ð Â·Ð Â°Ð ÐÐ¡ÐÐ¡âÐ¡â¹. Ð Â§Ð¡âÐ ÑÐ Â±Ð¡â¹ Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÑÐ¡âÐ¡Ð Ð ÐÐ ÑÐ ÐÐ¡â¹Ð â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò, Ð¡ÐÐ ÐÐ Â°Ð¡â¡Ð Â°Ð Â»Ð Â° Ð¡ÑÐ ÒÐ Â°Ð Â»Ð ÑÐ¡âÐ Âµ Ð¡ÐÐ¡âÐ Â°Ð¡ÐÐ¡â¹Ð â.\n\n"
        
        if not slots:
            message += "Ð Ð Ð ÐÐ Â°Ð¡Ð Ð ÑÐ ÑÐ ÑÐ Â° Ð ÐÐ ÂµÐ¡â Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ¡âÐ ÐÐ ÐÐ¡â¹Ð¡â¦ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð.\nÐ ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð âÐ¡âÐ Âµ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð Ñ Ð ÐÐ Â°Ð Â¶Ð ÑÐ ÑÐ¡âÐ Âµ ÐÂ«?? Ð ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÑÐ¡âÐ¡ÐÐÂ»!"
            keyboard = [[InlineKeyboardButton("?? Ð ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò", callback_data='do_tarot')], [InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=message, reply_markup=reply_markup)
            return
        
        keyboard = []
        for slot_num in sorted(slots.keys()):
            timestamp = slots[slot_num]
            keyboard.append([InlineKeyboardButton(f"?? Ð ÐÐ¡â¡Ð ÂµÐ âÐ ÑÐ Â° #{slot_num} ({timestamp})", callback_data=f'view_slot_{slot_num}')])
        keyboard.append([InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data.startswith('view_slot_'):
        slot_num = int(query.data.split('_')[2])
        reading = get_saved_reading(user_id, slot_num)
        if reading:
            cards_str, interpretation, timestamp = reading
            message = f"?? Ð Â Ð ÑÐ ÐÐ ÑÐ âºÐ ÑÐ â Ð ÂÐ â Ð ÐÐ Â§Ð â¢Ð â¢Ð ÑÐ Â #{slot_num}\n?? {timestamp[:16]}\n\n{interpretation}"
            keyboard = [[InlineKeyboardButton("? Ð ÐÐ ÒÐ Â°Ð Â»Ð ÑÐ¡âÐ¡Ð Ð¡ÐÐ¡âÐ ÑÐ¡â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò", callback_data=f'delete_slot_{slot_num}')], [InlineKeyboardButton("?? Ð ÑÐ Â°Ð Â·Ð Â°Ð Ò Ð Ñ Ð¡ÐÐ ÑÐ ÑÐ¡ÐÐ ÑÐ¡Ñ", callback_data='saved_readings')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="? Ð Â Ð Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð ÐÐ Âµ Ð ÐÐ Â°Ð âÐ ÒÐ ÂµÐ Ð.")
    
    elif query.data == 'balance':
        balance = get_balance(user_id)
        message = (
            f"?? Ð âÐ ÑÐ Ð Ð ÑÐ â¢Ð ÑÐ ÐÐ Â©Ð ÂÐ â¢ Ð âÐ ÑÐ âºÐ ÑÐ ÑÐ Ð ??\n"
            f"\n?? Ð âÐ ÑÐ¡ÐÐ¡âÐ¡ÑÐ ÑÐ ÐÐ Ñ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð: {balance}\n"
            f"\n? Ð ÑÐ Â°Ð Ñ Ð ÑÐ ÑÐ Â»Ð¡ÑÐ¡â¡Ð ÑÐ¡âÐ¡Ð Ð Â±Ð ÑÐ Â»Ð¡ÐÐ¡â¬Ð Âµ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð:\n"
            f"Ð²ÐÑ Ð ÑÐ¡ÐÐ ÑÐ ÑÐ Â»Ð Â°Ð¡ÐÐ ÑÐ¡âÐ Âµ Ð ÒÐ¡ÐÐ¡ÑÐ ÑÐ Â° Ð²Ðâ +1 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò ??\n"
            f"Ð²ÐÑ Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡â¬Ð ÑÐ¡âÐ ÂµÐ¡ÐÐ¡Ð Ð ÐÐ Â° Ð ÑÐ Â°Ð ÐÐ Â°Ð Â» Ð²Ðâ +3 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â° ??\n"
            f"Ð²ÐÑ Ð ÑÐ¡ÑÐ ÑÐ ÑÐ¡âÐ Âµ Ð ÑÐ Â°Ð ÑÐ ÂµÐ¡â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð Ð¡ÐÐ Ñ Ð¡ÐÐ ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ â ??"
        )
        keyboard = [
            [InlineKeyboardButton("?? Ð ÑÐ¡ÑÐ ÑÐ ÑÐ¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹", callback_data='buy_packs')],
            [InlineKeyboardButton("?? Ð ÑÐ¡ÐÐ ÑÐ ÑÐ Â»Ð Â°Ð¡ÐÐ ÑÐ¡âÐ¡Ð Ð ÒÐ¡ÐÐ¡ÑÐ ÑÐ Â°", callback_data='referral')],
            [InlineKeyboardButton("?? Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ Â°Ð¡âÐ¡ÐÐ¡ÐÐ¡Ð (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'referral':
        ref_link = f"https://t.me/cardnotlie_bot?start={user_id}"
        referral_count = get_referral_count(user_id)
        message = (
            f"?? Ð Â Ð â¢Ð Â¤Ð â¢Ð Â Ð ÑÐ âºÐ Â¬Ð ÑÐ ÑÐ Ð Ð ÑÐ Â Ð ÑÐ âÐ Â Ð ÑÐ ÑÐ ÑÐ Ñ ??\n\n"
            f"? Ð âÐ Â°Ð¡â¬Ð Â° Ð¡ÐÐ ÂµÐ¡âÐ ÂµÐ¡ÐÐ Â°Ð Â»Ð¡ÐÐ ÐÐ Â°Ð¡Ð Ð¡ÐÐ¡ÐÐ¡â¹Ð Â»Ð ÑÐ Â°:\n"
            f"{ref_link}\n\n"
            f"?? Ð ÑÐ¡ÐÐ ÑÐ ÑÐ Â»Ð Â°Ð¡â¬Ð ÂµÐ ÐÐ Ñ Ð ÒÐ¡ÐÐ¡ÑÐ Â·Ð ÂµÐ â: {referral_count}\n"
            f"?? Ð âÐ Â° Ð ÑÐ Â°Ð Â¶Ð ÒÐ ÑÐ ÑÐ Ñ Ð ÒÐ¡ÐÐ¡ÑÐ ÑÐ Â° Ð²Ðâ +1 Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ Â»Ð Â°Ð¡âÐ ÐÐ¡â¹Ð â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò!\n\n"
            f"?? Ð ÑÐ¡ÐÐ ÑÐ¡ÐÐ¡âÐ Ñ Ð ÑÐ¡âÐ ÑÐ¡ÐÐ Â°Ð ÐÐ¡ÐÐ¡âÐ Âµ Ð¡ÐÐ¡ÐÐ¡â¹Ð Â»Ð ÑÐ¡Ñ Ð ÒÐ¡ÐÐ¡ÑÐ Â·Ð¡ÐÐ¡ÐÐ Ñ Ð ÑÐ Â»Ð Ñ Ð Ð Ð¡ÐÐ ÑÐ¡â Ð¡ÐÐ ÂµÐ¡âÐ Ñ!"
        )
        keyboard = [[InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'buy_packs':
        message = (
            "?? Ð ÐÐ ÑÐ ÑÐ ÐÐ ÑÐ âÐ Â« Ð ÑÐ ÑÐ âºÐ ÑÐ ÑÐ Â« ??\n"
            "\nÐ âÐ¡â¹Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ¡âÐ Âµ Ð¡ÑÐ ÒÐ ÑÐ Â±Ð ÐÐ¡â¹Ð â Ð¡ÐÐ ÑÐ ÑÐ¡ÐÐ ÑÐ Â±:\n"
            "\n?? Ð âÐ Â°Ð ÐÐ ÑÐ ÑÐ ÐÐ¡ÐÐ ÑÐ Â°Ð¡Ð Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â° Ð²Ðâ Ð¡âÐ¡ÐÐ ÂµÐ Â±Ð¡ÑÐ ÂµÐ¡âÐ¡ÐÐ¡Ð Ð¡ÐÐ¡ÑÐ¡â¡Ð ÐÐ Â°Ð¡Ð Ð ÑÐ¡ÐÐ ÑÐ ÐÐ ÂµÐ¡ÐÐ ÑÐ Â° Ð¡ÐÐ ÑÐ¡ÐÐ ÑÐ ÐÐ¡â¬Ð ÑÐ¡âÐ Â° ?\n"
            "?? Ð ÑÐ¡ÐÐ ÑÐ ÑÐ¡âÐ ÑÐ ÐÐ Â°Ð Â»Ð¡ÐÐ¡âÐ Â° Ð²Ðâ Ð Ð Ð¡ÐÐ Â°Ð Â·Ð¡ÐÐ Â°Ð Â±Ð ÑÐ¡âÐ ÑÐ Âµ ??"
        )
        keyboard = [
            [InlineKeyboardButton("?? Ð âÐ Â°Ð ÐÐ ÑÐ ÑÐ ÐÐ¡ÐÐ ÑÐ Â°Ð¡Ð Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â°", callback_data='card_packs')],
            [InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'card_packs':
        message = (
            "?? Ð ÑÐ ÑÐ ÑÐ â¢Ð ÑÐ Â« Ð Â Ð ÑÐ ÐÐ ÑÐ âºÐ ÑÐ âÐ ÑÐ â ??\n"
            "\n? Ð âÐ¡â¹Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ¡âÐ Âµ Ð ÑÐ Â°Ð ÑÐ ÂµÐ¡â Ð¡ÐÐ Ñ Ð¡ÐÐ ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ â:\n"
            "\n?? 1 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð²Ðâ 100 ?\n"
            "   Ð ÂÐ ÒÐ ÂµÐ Â°Ð Â»Ð¡ÐÐ ÐÐ Ñ Ð ÒÐ Â»Ð¡Ð Ð¡ÐÐ Â°Ð Â·Ð ÑÐ ÐÐ ÑÐ ÑÐ Ñ Ð ÑÐ Â°Ð ÒÐ Â°Ð ÐÐ ÑÐ¡Ð.\n"
            "\n?? 3 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â° Ð²Ðâ 285 ? (-5%)\n"
            "   Ð Â­Ð ÑÐ ÑÐ ÐÐ ÑÐ ÑÐ ÑÐ¡Ð 15 ?.\n"
            "\n?? 7 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð Ð²Ðâ 630 ? (-10%)\n"
            "   Ð Â­Ð ÑÐ ÑÐ ÐÐ ÑÐ ÑÐ ÑÐ¡Ð 70 ?.\n"
            "\n?? 13 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð Ð²Ðâ 1 105 ? (-15%)\n"
            "   Ð Â­Ð ÑÐ ÑÐ ÐÐ ÑÐ ÑÐ ÑÐ¡Ð 195 ?."
        )
        keyboard = [
            [InlineKeyboardButton("1 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð²Ðâ 100?", callback_data='buy_1')],
            [InlineKeyboardButton("3 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â° Ð²Ðâ 285? (-5%)", callback_data='buy_3')],
            [InlineKeyboardButton("7 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð Ð²Ðâ 630? (-10%)", callback_data='buy_7')],
            [InlineKeyboardButton("13 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð Ð²Ðâ 1 105? (-15%)", callback_data='buy_13')],
            [InlineKeyboardButton("?? Ð ÑÐ Â°Ð Â·Ð Â°Ð Ò", callback_data='buy_packs')]
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
            f"?? Ð ÑÐ ÑÐ âºÐ ÑÐ ÑÐ Ñ Ð ÑÐ ÑÐ ÑÐ â¢Ð ÑÐ Ñ: {pack_size} Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð ??\n"
            f"\n?? Ð ÐÐ¡âÐ ÑÐ ÑÐ ÑÐ ÑÐ¡ÐÐ¡âÐ¡Ð: {price} ? (Ð¡ÐÐ ÑÐ ÑÐ ÒÐ ÑÐ Â° {discount})\n"
            f"\n?? Ð Â Ð ÂµÐ ÑÐ ÐÐ ÑÐ Â·Ð ÑÐ¡âÐ¡â¹ Ð ÒÐ Â»Ð¡Ð Ð ÑÐ ÑÐ Â»Ð Â°Ð¡âÐ¡â¹:\n"
            f"?? Ð âÐ Â°Ð ÐÐ Ñ: Ð Â Ð Â°Ð âÐ¡âÐ¡âÐ Â°Ð âÐ Â·Ð ÂµÐ ÐÐ Â±Ð Â°Ð ÐÐ Ñ.\n"
            f"?? Ð ÑÐ ÑÐ ÑÐ ÂµÐ¡Ð Ð ÑÐ Â°Ð¡ÐÐ¡âÐ¡â¹: \n"
            f"?? Ð ÑÐ ÑÐ Â»Ð¡ÑÐ¡â¡Ð Â°Ð¡âÐ ÂµÐ Â»Ð¡Ð: Ð ÐÐ ÂµÐ¡ÐÐ ÑÐ ÂµÐ â Ð âº.\n"
            f"?? Ð ÐÐ¡ÑÐ ÑÐ ÑÐ Â°: {price} ?.\n"
            f"\n? Ð ÑÐ ÑÐ ÐÐ âºÐ â¢ Ð ÑÐ ÑÐ âºÐ ÑÐ ÑÐ Â«:\n"
            f"1. Ð ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð âÐ¡âÐ Âµ Ð¡ÐÐ ÑÐ¡ÐÐ ÑÐ ÐÐ¡â¬Ð ÑÐ¡â Ð ÑÐ ÂµÐ¡ÐÐ ÂµÐ ÐÐ ÑÐ ÒÐ Â°.\n"
            f"2. Ð ÑÐ Â°Ð ÑÐ ÑÐ¡â¬Ð ÑÐ¡âÐ Âµ Ð Ð Ð ÑÐ ÑÐ ÒÐ ÒÐ ÂµÐ¡ÐÐ Â¶Ð ÑÐ¡Ñ @jobphone_admin Ð¡Ð Ð ÑÐ ÑÐ ÑÐ ÂµÐ¡âÐ ÑÐ ÑÐ â ÐÂ«Ð ÑÐ ÑÐ âºÐ ÑÐ ÑÐ ÑÐÂ».\n"
            f"3. Ð ÑÐ¡â¹ Ð ÐÐ Â°Ð¡â¡Ð ÑÐ¡ÐÐ Â»Ð ÑÐ Ñ {pack_size} Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð Ð ÐÐ Â° Ð ÐÐ Â°Ð¡â¬ Ð Â±Ð Â°Ð Â»Ð Â°Ð ÐÐ¡Ð Ð Ð Ð¡âÐ ÂµÐ¡â¡Ð ÂµÐ ÐÐ ÑÐ Âµ 10 Ð ÑÐ ÑÐ ÐÐ¡ÑÐ¡â! ?\n"
            f"\n?? Ð ÑÐ ÑÐ ÒÐ¡ÐÐ ÑÐ Â±Ð ÐÐ ÂµÐ Âµ Ð ÑÐ Â± Ð¡ÑÐ¡ÐÐ Â»Ð ÑÐ ÐÐ ÑÐ¡ÐÐ¡â¦ Ð ÑÐ ÑÐ Â»Ð Â°Ð¡âÐ¡â¹: /terms"
        )
        keyboard = [
            [InlineKeyboardButton("?? Ð ÑÐ Â°Ð Â·Ð Â°Ð Ò Ð Ñ Ð ÑÐ Â°Ð ÑÐ ÂµÐ¡âÐ Â°Ð Ñ", callback_data='card_packs')],
            [InlineKeyboardButton("?? Ð ÐÐ¡ÐÐ Â»Ð ÑÐ ÐÐ ÑÐ¡Ð Ð ÑÐ ÑÐ Â»Ð Â°Ð¡âÐ¡â¹", callback_data='terms')],
            [InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'terms' or query.data == 'terms_button':
        message = (
            "?? Ð ÐÐ ÐÐ âºÐ ÑÐ âÐ ÂÐ Ð Ð ÑÐ ÑÐ âºÐ ÑÐ ÑÐ Â« Ð Â Ð ÐÐ ÑÐ âÐ âºÐ ÑÐ ÐÐ ÂÐ â¢ ??\n"
            "\n?? Ð âÐ ÑÐ âÐ ÑÐ Ñ: Ð Â»Ð¡ÐÐ Â±Ð Â°Ð¡Ð Ð ÑÐ ÑÐ Â»Ð Â°Ð¡âÐ Â° Ð Ð Ð¡ÐÐ¡âÐ ÑÐ Ñ Ð Â±Ð ÑÐ¡âÐ Âµ Ð¡ÐÐ ÐÐ Â»Ð¡ÐÐ ÂµÐ¡âÐ¡ÐÐ¡Ð Ð âÐ ÑÐ âÐ Â Ð ÑÐ âÐ ÑÐ âºÐ Â¬Ð ÑÐ Â«Ð Ñ Ð âÐ ÑÐ ÑÐ ÑÐ ÑÐ ÑÐ Ñ.\n"
            "Ð Â Ð Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹ Ð ÑÐ Â°Ð¡ÐÐ Ñ Ð ÑÐ¡ÐÐ ÂµÐ ÒÐ ÑÐ¡ÐÐ¡âÐ Â°Ð ÐÐ Â»Ð¡ÐÐ¡ÐÐ¡âÐ¡ÐÐ¡Ð Ð Ð Ð¡ÐÐ Â°Ð Â·Ð ÐÐ Â»Ð ÂµÐ ÑÐ Â°Ð¡âÐ ÂµÐ Â»Ð¡ÐÐ ÐÐ¡â¹Ð¡â¦ Ð¡â Ð ÂµÐ Â»Ð¡ÐÐ¡â¦.\n"
            "Ð ÂÐ ÐÐ¡âÐ ÂµÐ¡ÐÐ ÑÐ¡ÐÐ ÂµÐ¡âÐ Â°Ð¡â Ð ÑÐ Ñ Ð ÑÐ Â°Ð¡ÐÐ¡â Ð ÐÐ Âµ Ð¡ÐÐ ÐÐ Â»Ð¡ÐÐ¡ÐÐ¡âÐ¡ÐÐ¡Ð Ð ÑÐ¡ÐÐ ÂµÐ ÒÐ¡ÐÐ ÑÐ Â°Ð Â·Ð Â°Ð ÐÐ ÑÐ ÂµÐ Ñ Ð Â±Ð¡ÑÐ ÒÐ¡ÑÐ¡â°Ð ÂµÐ ÑÐ Ñ Ð Ñ Ð ÐÐ Âµ Ð Â·Ð Â°Ð ÑÐ ÂµÐ ÐÐ¡ÐÐ¡ÐÐ¡â Ð ÑÐ ÑÐ ÐÐ¡ÐÐ¡ÑÐ Â»Ð¡ÐÐ¡âÐ Â°Ð¡â Ð ÑÐ¡Ð Ð¡ÐÐ ÑÐ ÂµÐ¡â Ð ÑÐ Â°Ð Â»Ð ÑÐ¡ÐÐ¡âÐ Â°.\n"
            "\n? Ð ÑÐ Â°Ð Â¶Ð ÑÐ ÑÐ Â°Ð¡Ð ÐÂ«Ð ÑÐ ÑÐ Â»Ð Â°Ð¡âÐ ÑÐ¡âÐ¡ÐÐÂ», Ð ÐÐ¡â¹ Ð¡ÐÐ ÑÐ ÑÐ Â»Ð Â°Ð¡â¬Ð Â°Ð ÂµÐ¡âÐ ÂµÐ¡ÐÐ¡Ð Ð¡Ð Ð¡âÐ ÂµÐ Ñ, Ð¡â¡Ð¡âÐ Ñ:\n"
            "Ð²ÐÑ Ð ÑÐ ÑÐ Â»Ð Â°Ð¡âÐ Â° Ð ÒÐ ÑÐ Â±Ð¡ÐÐ ÑÐ ÐÐ ÑÐ Â»Ð¡ÐÐ ÐÐ Â°Ð¡Ð Ð Ñ Ð ÐÐ ÂµÐ ÑÐ Â±Ð¡ÐÐ Â·Ð Â°Ð¡âÐ ÂµÐ Â»Ð¡ÐÐ ÐÐ Â°Ð¡Ð.\n"
            "Ð²ÐÑ Ð Â Ð Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹ Ð ÐÐ ÑÐ¡ÐÐ¡ÐÐ¡â Ð¡ÐÐ Â°Ð Â·Ð ÐÐ Â»Ð ÂµÐ ÑÐ Â°Ð¡âÐ ÂµÐ Â»Ð¡ÐÐ ÐÐ¡â¹Ð â Ð¡â¦Ð Â°Ð¡ÐÐ Â°Ð ÑÐ¡âÐ ÂµÐ¡Ð.\n"
            "Ð²ÐÑ Ð âÐ¡â¹ Ð¡ÐÐ ÑÐ ÐÐ ÂµÐ¡ÐÐ¡â¬Ð Â°Ð ÂµÐ¡âÐ Âµ Ð ÑÐ Â»Ð Â°Ð¡âÐ¡âÐ Â¶ Ð ÑÐ Ñ Ð¡ÐÐ ÑÐ Â±Ð¡ÐÐ¡âÐ ÐÐ ÂµÐ ÐÐ ÐÐ ÑÐ â Ð ÐÐ ÑÐ Â»Ð Âµ Ð Â±Ð ÂµÐ Â· Ð ÑÐ¡ÐÐ ÑÐ ÐÐ¡ÑÐ Â¶Ð ÒÐ ÂµÐ ÐÐ ÑÐ¡Ð.\n"
            "Ð²ÐÑ Ð âÐ ÑÐ Â·Ð ÐÐ¡ÐÐ Â°Ð¡â Ð¡ÐÐ¡ÐÐ ÂµÐ ÒÐ¡ÐÐ¡âÐ Ð Ð ÐÐ Âµ Ð ÑÐ¡ÐÐ ÂµÐ ÒÐ¡ÑÐ¡ÐÐ ÑÐ ÑÐ¡âÐ¡ÐÐ ÂµÐ Ð (Ð ÒÐ ÑÐ Â±Ð¡ÐÐ ÑÐ ÐÐ ÑÐ Â»Ð¡ÐÐ ÐÐ¡â¹Ð â Ð ÒÐ ÑÐ ÐÐ Â°Ð¡â).\n"
            "\n? Ð ÐÐ ÑÐ Â°Ð¡ÐÐ ÑÐ Â±Ð Ñ Ð Â·Ð Â° Ð ÑÐ ÑÐ ÒÐ ÒÐ ÂµÐ¡ÐÐ Â¶Ð ÑÐ¡Ñ Ð ÑÐ¡ÐÐ ÑÐ ÂµÐ ÑÐ¡âÐ Â°! ??"
        )
        keyboard = [[InlineKeyboardButton("?? Ð ÑÐ Â°Ð Â·Ð Â°Ð Ò Ð Ñ Ð ÑÐ ÑÐ Â»Ð Â°Ð¡âÐ Âµ", callback_data='buy_packs')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'subscribe':
        subscribed = check_subscribed(user_id)
        if subscribed:
            message = "? Ð âÐ¡â¹ Ð¡ÑÐ Â¶Ð Âµ Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ Â°Ð ÐÐ¡â¹ Ð ÐÐ Â° Ð ÐÐ Â°Ð¡â¬ Ð ÑÐ Â°Ð ÐÐ Â°Ð Â»!\n?? Ð âÐ ÑÐ ÐÐ¡ÑÐ¡Ð +3 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â° Ð¡ÑÐ Â¶Ð Âµ Ð ÐÐ Â°Ð¡â¡Ð ÑÐ¡ÐÐ Â»Ð ÂµÐ Ð."
        else:
            message = (
                "?? Ð ÑÐ ÑÐ âÐ ÑÐ ÂÐ ÐÐ ÑÐ Ñ Ð ÑÐ Ñ Ð ÑÐ ÑÐ ÑÐ ÑÐ âº ??\n"
                "\nÐ ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡â¬Ð ÑÐ¡âÐ ÂµÐ¡ÐÐ¡Ð Ð ÐÐ Â° Ð ÐÐ Â°Ð¡â¬ Ð¡ÐÐ Â·Ð ÑÐ¡âÐ ÂµÐ¡ÐÐ ÑÐ¡â¡Ð ÂµÐ¡ÐÐ ÑÐ ÑÐ â Ð ÑÐ Â°Ð ÐÐ Â°Ð Â» Ð Ñ Ð ÑÐ ÑÐ Â»Ð¡ÑÐ¡â¡Ð ÑÐ¡âÐ Âµ +3 Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ Â»Ð Â°Ð¡âÐ ÐÐ¡â¹Ð¡â¦ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â°!\n"
                "\n? Ð ÑÐ Â°Ð ÐÐ Â°Ð Â»: https://t.me/+5q7VJBPU4_QyMDky\n"
                "\nÐ ÑÐ ÑÐ¡ÐÐ Â»Ð Âµ Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ ÑÐ Ñ Ð ÐÐ Â°Ð Â¶Ð ÑÐ ÑÐ¡âÐ Âµ Ð ÑÐ ÐÐ ÑÐ ÑÐ ÑÐ¡Ñ Ð ÐÐ ÑÐ Â¶Ð Âµ:"
            )
        keyboard = [
            [InlineKeyboardButton("?? Ð ÑÐ ÂµÐ¡ÐÐ ÂµÐ âÐ¡âÐ Ñ Ð Ð Ð ÑÐ Â°Ð ÐÐ Â°Ð Â»", url="https://t.me/+5q7VJBPU4_QyMDky")],
            [InlineKeyboardButton("? Ð Ð Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ Â°Ð Â»Ð¡ÐÐ¡Ð (+3 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â°)", callback_data='confirm_subscribe')],
            [InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'confirm_subscribe':
        subscribed_db = check_subscribed(user_id)
        
        if subscribed_db:
            message = "? Ð âÐ¡â¹ Ð¡ÑÐ Â¶Ð Âµ Ð ÑÐ ÑÐ Â»Ð¡ÑÐ¡â¡Ð ÑÐ Â»Ð Ñ Ð Â±Ð ÑÐ ÐÐ¡ÑÐ¡Ð Ð Â·Ð Â° Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ ÑÐ¡Ñ!"
        else:
            try:
                chat_member = await context.bot.get_chat_member(
                    chat_id="@+5q7VJBPU4_QyMDky",
                    user_id=user_id
                )
                if chat_member.status in ["member", "administrator", "creator"]:
                    mark_subscribed(user_id)
                    message = "?? Ð ÐÐ¡ÐÐ Â°! Ð âÐ¡â¹ Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ Â°Ð Â»Ð ÑÐ¡ÐÐ¡Ð Ð ÐÐ Â° Ð ÑÐ Â°Ð ÐÐ Â°Ð Â»!\n? Ð âÐ ÑÐ ÐÐ¡ÑÐ¡Ð +3 Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ Â»Ð Â°Ð¡âÐ ÐÐ¡â¹Ð¡â¦ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â° Ð ÐÐ Â°Ð¡â¡Ð ÑÐ¡ÐÐ Â»Ð ÂµÐ Ð Ð ÐÐ Â° Ð ÐÐ Â°Ð¡â¬ Ð¡ÐÐ¡â¡Ð¡âÐ¡â!"
                else:
                    message = "? Ð âÐ¡â¹ Ð ÐÐ Âµ Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ Â°Ð ÐÐ¡â¹ Ð ÐÐ Â° Ð ÑÐ Â°Ð ÐÐ Â°Ð Â».\nÐ ÑÐ ÑÐ Â¶Ð Â°Ð Â»Ð¡ÑÐ âÐ¡ÐÐ¡âÐ Â°, Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡â¬Ð ÑÐ¡âÐ ÂµÐ¡ÐÐ¡Ð Ð Ñ Ð ÐÐ Â°Ð Â¶Ð ÑÐ ÑÐ¡âÐ Âµ Ð ÑÐ ÐÐ ÑÐ ÑÐ ÑÐ¡Ñ Ð¡ÐÐ ÐÐ ÑÐ ÐÐ Â°."
            except Exception as e:
                print(f"Ð ÑÐ¡â¬Ð ÑÐ Â±Ð ÑÐ Â° Ð ÑÐ¡ÐÐ ÑÐ ÐÐ ÂµÐ¡ÐÐ ÑÐ Ñ Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ ÑÐ Ñ: {e}")
                message = "? Ð ÑÐ Âµ Ð¡ÑÐ ÒÐ Â°Ð Â»Ð ÑÐ¡ÐÐ¡Ð Ð ÑÐ¡ÐÐ ÑÐ ÐÐ ÂµÐ¡ÐÐ ÑÐ¡âÐ¡Ð Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ ÑÐ¡Ñ. Ð ÑÐ ÑÐ ÑÐ¡ÐÐ ÑÐ Â±Ð¡ÑÐ âÐ¡âÐ Âµ Ð ÑÐ ÑÐ Â·Ð Â¶Ð Âµ."
        
        keyboard = [[InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'help':
        message = (
            "? Ð ÑÐ ÑÐ ÑÐ ÑÐ Â©Ð Â¬ ?\n"
            "\n? Ð ÑÐ ÑÐ Ñ Ð ÑÐ ÑÐ âºÐ Â¬Ð âÐ ÑÐ âÐ ÑÐ ÑÐ Â¬Ð ÐÐ Ð Ð âÐ ÑÐ ÑÐ ÑÐ Ñ:\n"
            "Ð²ÐÑ ?? Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â° Ð ÒÐ ÐÐ¡Ð Ð²Ðâ Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ Â»Ð Â°Ð¡âÐ ÐÐ ÑÐ Âµ Ð ÑÐ Â°Ð ÒÐ Â°Ð ÐÐ ÑÐ Âµ Ð ÐÐ Â° Ð¡ÐÐ ÂµÐ ÑÐ ÑÐ ÒÐ ÐÐ¡Ð (1 Ð¡ÐÐ Â°Ð Â· Ð Ð Ð ÒÐ ÂµÐ ÐÐ¡Ð)\n"
            "Ð²ÐÑ ?? Ð ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð²Ðâ Ð ÑÐ ÑÐ ÒÐ¡ÐÐ ÑÐ Â±Ð ÐÐ¡â¹Ð â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð ÑÐ Â· 3+ Ð ÑÐ Â°Ð¡ÐÐ¡â (Ð¡ÐÐ ÑÐ ÑÐ¡ÐÐ¡â¹Ð ÐÐ Â°Ð ÂµÐ¡âÐ¡ÐÐ¡Ð Ð¡Ð Ð Â±Ð Â°Ð Â»Ð Â°Ð ÐÐ¡ÐÐ Â°)\n"
            "Ð²ÐÑ ?? Ð ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÑÐ¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò Ð²Ðâ Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÑÐ¡âÐ Âµ Ð¡ÐÐ ÂµÐ Â·Ð¡ÑÐ Â»Ð¡ÐÐ¡âÐ Â°Ð¡â Ð Ð Ð ÑÐ ÒÐ ÐÐ¡Ñ Ð ÑÐ Â· 3 Ð¡ÐÐ¡â¡Ð ÂµÐ ÂµÐ Ñ\n"
            "\n??? Ð ÐÐ ÑÐ ÒÐ Â Ð ÑÐ ÑÐ â¢Ð ÑÐ ÂÐ â¢ Ð Â Ð ÑÐ ÐÐ ÑÐ âºÐ ÑÐ âÐ ÑÐ â:\n"
            "Ð²ÐÑ Ð Ð Ð ÐÐ Â°Ð¡Ð Ð ÂµÐ¡ÐÐ¡âÐ¡Ð 3 Ð¡ÐÐ¡â¡Ð ÂµÐ âÐ ÑÐ Ñ Ð ÒÐ Â»Ð¡Ð Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ ÂµÐ ÐÐ ÑÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð.\n"
            "Ð²ÐÑ Ð Â Ð Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹ Ð ÑÐ â¢ Ð¡ÐÐ ÑÐ¡â¦Ð¡ÐÐ Â°Ð ÐÐ¡ÐÐ¡ÐÐ¡âÐ¡ÐÐ¡Ð Ð Â°Ð ÐÐ¡âÐ ÑÐ ÑÐ Â°Ð¡âÐ ÑÐ¡â¡Ð ÂµÐ¡ÐÐ ÑÐ Ñ Ð²Ðâ Ð¡âÐ ÑÐ Â»Ð¡ÐÐ ÑÐ Ñ Ð ÑÐ Ñ Ð ÐÐ Â°Ð¡â¬Ð ÂµÐ ÑÐ¡Ñ Ð ÐÐ¡â¹Ð Â±Ð ÑÐ¡ÐÐ¡Ñ.\n"
            "Ð²ÐÑ Ð â¢Ð¡ÐÐ Â»Ð Ñ Ð ÐÐ¡ÐÐ Âµ Ð¡ÐÐ¡â¡Ð ÂµÐ âÐ ÑÐ Ñ Ð Â·Ð Â°Ð ÐÐ¡ÐÐ¡âÐ¡â¹ Ð²Ðâ Ð¡ÐÐ ÐÐ Â°Ð¡â¡Ð Â°Ð Â»Ð Â° Ð¡ÑÐ ÒÐ Â°Ð Â»Ð ÑÐ¡âÐ Âµ Ð¡ÐÐ¡âÐ Â°Ð¡ÐÐ¡â¹Ð â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò.\n"
            "\n?? Ð âÐ ÑÐ âºÐ ÑÐ ÑÐ Ð:\n"
            "Ð²ÐÑ Ð ÑÐ¡ÐÐ Ñ Ð¡ÐÐ ÂµÐ ÑÐ ÑÐ¡ÐÐ¡âÐ¡ÐÐ Â°Ð¡â Ð ÑÐ Ñ: 1 Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ Â»Ð Â°Ð¡âÐ ÐÐ¡â¹Ð â Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò.\n"
            "Ð²ÐÑ ?? Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â° Ð ÒÐ ÐÐ¡Ð Ð²Ðâ Ð ÐÐ¡ÐÐ ÂµÐ ÑÐ ÒÐ Â° Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ Â»Ð Â°Ð¡âÐ ÐÐ Ñ, 1 Ð¡ÐÐ Â°Ð Â· Ð Ð Ð ÒÐ ÂµÐ ÐÐ¡Ð.\n"
            "Ð²ÐÑ Ð âÐ Â° Ð ÒÐ¡ÐÐ¡ÑÐ ÑÐ Â°: +1 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò.\n"
            "Ð²ÐÑ Ð âÐ Â° Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ ÑÐ¡Ñ: +3 Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ Â°.\n"
            "Ð²ÐÑ Ð ÑÐ ÑÐ ÑÐ¡ÑÐ ÑÐ ÑÐ Â° Ð ÑÐ Â°Ð ÑÐ ÂµÐ¡âÐ ÑÐ Ð Ð¡ÐÐ Ñ Ð¡ÐÐ ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ â Ð ÒÐ Ñ 15%.\n"
            "\n?? Ð ÑÐ ÑÐ âºÐ ÑÐ ÑÐ Ñ:\n"
            "Ð²ÐÑ Ð âÐ Â°Ð ÐÐ ÑÐ ÑÐ ÐÐ¡ÐÐ ÑÐ Â°Ð¡Ð Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â° Ð²Ðâ Ð¡ÐÐ¡ÑÐ¡â¡Ð ÐÐ Â°Ð¡Ð Ð ÑÐ¡ÐÐ ÑÐ ÐÐ ÂµÐ¡ÐÐ ÑÐ Â° Ð¡ÐÐ ÑÐ¡ÐÐ ÑÐ ÐÐ¡â¬Ð ÑÐ¡âÐ Â° ?\n"
            "Ð²ÐÑ Ð ÑÐ¡ÐÐ ÑÐ ÑÐ¡âÐ ÑÐ ÐÐ Â°Ð Â»Ð¡ÐÐ¡âÐ Â° Ð²Ðâ Ð Ð Ð¡ÐÐ Â°Ð Â·Ð¡ÐÐ Â°Ð Â±Ð ÑÐ¡âÐ ÑÐ Âµ ??\n"
            "Ð²ÐÑ Ð ÑÐ ÑÐ ÒÐ¡ÐÐ ÑÐ Â±Ð ÐÐ ÂµÐ Âµ Ð ÑÐ Â± Ð¡ÑÐ¡ÐÐ Â»Ð ÑÐ ÐÐ ÑÐ¡ÐÐ¡â¦: /terms"
        )
        keyboard = [[InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'back_to_menu':
        user_data = get_user_data(user_id)
        if not user_data or not user_data.get('name'):
            await query.message.reply_text("Ð ÑÐ Â°Ð ÑÐ ÑÐ¡â¬Ð ÑÐ¡âÐ Âµ Ð¡ÐÐ ÐÐ ÑÐ¡â Ð ÑÐ ÑÐ¡Ð:")
            return
        
        balance = get_balance(user_id)
        message = f"?? Ð âÐ ÑÐ âÐ Â Ð Ñ Ð ÑÐ ÑÐ âÐ ÑÐ âºÐ ÑÐ âÐ ÑÐ ÑÐ Â¬ Ð â Ð ÑÐ ÂÐ Â  Ð ÑÐ ÑÐ Â Ð Ñ! ??\n? {user_data['name']}, Ð ÐÐ Â°Ð¡â¬ Ð Â±Ð Â°Ð Â»Ð Â°Ð ÐÐ¡Ð: {balance} Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð"
        keyboard = [
            [InlineKeyboardButton("?? Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â° Ð ÒÐ ÐÐ¡Ð (Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ Â»Ð Â°Ð¡âÐ ÐÐ Ñ)", callback_data='daily_card')],
            [InlineKeyboardButton("?? Ð ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò", callback_data='do_tarot')],
            [InlineKeyboardButton(f"?? Ð âÐ Â°Ð Â»Ð Â°Ð ÐÐ¡Ð: {balance}", callback_data='balance')],
            [InlineKeyboardButton("?? Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ ÑÐ Â° (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("??? Ð ÑÐ ÑÐ Ñ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹", callback_data='saved_readings')],
            [InlineKeyboardButton("? Ð ÑÐ ÑÐ ÑÐ ÑÐ¡â°Ð¡Ð", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)

async def choose_spread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name'):
        await query.message.reply_text("Ð ÐÐ ÐÐ Â°Ð¡â¡Ð Â°Ð Â»Ð Â° Ð¡ÑÐ ÑÐ Â°Ð Â¶Ð ÑÐ¡âÐ Âµ Ð ÑÐ ÑÐ¡Ð Ð Ñ Ð ÒÐ Â°Ð¡âÐ¡Ñ Ð¡ÐÐ ÑÐ Â¶Ð ÒÐ ÂµÐ ÐÐ ÑÐ¡Ð Ð¡â¡Ð ÂµÐ¡ÐÐ ÂµÐ Â· /start")
        return
    
    balance = get_balance(user_id)
    if balance <= 0:
        keyboard = [
            [InlineKeyboardButton("?? Ð ÑÐ¡ÑÐ ÑÐ ÑÐ¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹", callback_data='buy_packs')],
            [InlineKeyboardButton("?? Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ Â°Ð¡âÐ¡ÐÐ¡ÐÐ¡Ð (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("?? Ð ÑÐ ÂµÐ ÐÐ¡Ð", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="?? Ð Ð Ð ÐÐ Â°Ð¡Ð Ð Â·Ð Â°Ð ÑÐ ÑÐ ÐÐ¡â¡Ð ÑÐ Â»Ð ÑÐ¡ÐÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹.\n?? Ð ÑÐ ÑÐ ÑÐ ÑÐ Â»Ð ÐÐ ÑÐ¡âÐ Âµ Ð Â±Ð Â°Ð Â»Ð Â°Ð ÐÐ¡Ð Ð ÑÐ Â»Ð Ñ Ð ÑÐ ÑÐ Â»Ð¡ÑÐ¡â¡Ð ÑÐ¡âÐ Âµ Ð Â±Ð ÑÐ ÐÐ¡ÑÐ¡ÐÐ¡â¹!",
            reply_markup=reply_markup
        )
        return
    
    spreads = get_spread_options()
    spreads.pop('daily', None)
    
    message = "?? Ð âÐ Â«Ð âÐ â¢Ð Â Ð ÂÐ ÑÐ â¢ Ð ÑÐ ÂÐ Ñ Ð Â Ð ÑÐ ÐÐ ÑÐ âºÐ ÑÐ âÐ Ñ ??\n\n"
    keyboard = []
    
    for spread_id, spread_info in spreads.items():
        keyboard.append([InlineKeyboardButton(spread_info['name'], callback_data=f'spread_{spread_id}')])
    
    keyboard.append([InlineKeyboardButton("?? Ð ÑÐ Â°Ð Â·Ð Â°Ð Ò", callback_data='back_to_menu')])
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
    allow_reentry=True
)

async def reading_step_1_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await reading_step_1(update, context)

async def reading_step_2_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await reading_step_2(update, context)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if not user_data or not user_data.get('name'):
        await update.message.reply_text("Ð ÐÐ ÐÐ Â°Ð¡â¡Ð Â°Ð Â»Ð Â° Ð¡ÑÐ ÑÐ Â°Ð Â¶Ð ÑÐ¡âÐ Âµ Ð ÑÐ ÑÐ¡Ð Ð Ñ Ð ÒÐ Â°Ð¡âÐ¡Ñ Ð¡ÐÐ ÑÐ Â¶Ð ÒÐ ÂµÐ ÐÐ ÑÐ¡Ð Ð¡â¡Ð ÂµÐ¡ÐÐ ÂµÐ Â· /start")
        return
    
    balance = get_balance(user_id)
    message = f"?? Ð âÐ ÑÐ âÐ Â Ð Ñ Ð ÑÐ ÑÐ âÐ ÑÐ âºÐ ÑÐ âÐ ÑÐ ÑÐ Â¬ Ð â Ð ÑÐ ÂÐ Â  Ð ÑÐ ÑÐ Â Ð Ñ! ??\n? {user_data['name']}, Ð ÐÐ Â°Ð¡â¬ Ð Â±Ð Â°Ð Â»Ð Â°Ð ÐÐ¡Ð: {balance} Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ ÑÐ Ð"
    
    keyboard = [
        [InlineKeyboardButton("?? Ð ÑÐ Â°Ð¡ÐÐ¡âÐ Â° Ð ÒÐ ÐÐ¡Ð (Ð Â±Ð ÂµÐ¡ÐÐ ÑÐ Â»Ð Â°Ð¡âÐ ÐÐ Ñ)", callback_data='daily_card')],
        [InlineKeyboardButton("?? Ð ÐÐ ÒÐ ÂµÐ Â»Ð Â°Ð¡âÐ¡Ð Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð Ò", callback_data='do_tarot')],
        [InlineKeyboardButton(f"?? Ð âÐ Â°Ð Â»Ð Â°Ð ÐÐ¡Ð: {balance}", callback_data='balance')],
        [InlineKeyboardButton("?? Ð ÑÐ ÑÐ ÒÐ ÑÐ ÑÐ¡ÐÐ ÑÐ Â° (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("??? Ð ÑÐ ÑÐ Ñ Ð¡ÐÐ Â°Ð¡ÐÐ ÑÐ Â»Ð Â°Ð ÒÐ¡â¹", callback_data='saved_readings')],
        [InlineKeyboardButton("? Ð ÑÐ ÑÐ ÑÐ ÑÐ¡â°Ð¡Ð", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)
