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
                            text=f"?? РћС‚Р»РёС‡РЅРѕ! Р’Р°С€ РґСЂСѓРі {user.first_name} РїСЂРёСЃРѕРµРґРёРЅРёР»СЃСЏ!\nР’С‹ РїРѕР»СѓС‡РёР»Рё +1 СЂР°СЃРєР»Р°Рґ Рє Р±Р°Р»Р°РЅСЃСѓ!"
                        )
                    except: pass
        except: pass
    
    user_data = get_user_data(user.id)
    if not user_data or not user_data.get('name') or not user_data.get('birthdate'):
        await update.message.reply_text(
            "? Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ РІ РјРёСЂ РўР°СЂРѕ!\n\n"
            "?? Р”Р»СЏ РїРµСЂСЃРѕРЅР°Р»РёР·РёСЂРѕРІР°РЅРЅРѕРіРѕ РіР°РґР°РЅРёСЏ РјРЅРµ РЅСѓР¶РЅРѕ СѓР·РЅР°С‚СЊ РІР°СЃ РЅРµРјРЅРѕРіРѕ Р»СѓС‡С€Рµ.\n\n"
            "?? РЎРЅР°С‡Р°Р»Р° РЅР°РїРёС€РёС‚Рµ, РєР°Рє РІР°СЃ Р·РѕРІСѓС‚:"
        )
        return ASKING_NAME
    
    balance = get_balance(user.id)
    message = f"?? Р”РћР‘Р Рћ РџРћР–РђР›РћР’РђРўР¬ Р’ РњРР  РўРђР Рћ! ??\n? {user_data['name']}, РІР°С€ Р±Р°Р»Р°РЅСЃ: {balance} СЂР°СЃРєР»Р°РґРѕРІ"
    
    keyboard = [
        [InlineKeyboardButton("?? РљР°СЂС‚Р° РґРЅСЏ (Р±РµСЃРїР»Р°С‚РЅРѕ)", callback_data='daily_card')],
        [InlineKeyboardButton("?? РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')],
        [InlineKeyboardButton(f"?? Р‘Р°Р»Р°РЅСЃ: {balance}", callback_data='balance')],
        [InlineKeyboardButton("?? РџРѕРґРїРёСЃРєР° (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("??? РњРѕРё СЂР°СЃРєР»Р°РґС‹", callback_data='saved_readings')],
        [InlineKeyboardButton("? РџРѕРјРѕС‰СЊ", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)
    return ConversationHandler.END

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("? РРјСЏ РґРѕР»Р¶РЅРѕ Р±С‹С‚СЊ РЅРµ РјРµРЅРµРµ 2 СЃРёРјРІРѕР»РѕРІ. РџРѕРїСЂРѕР±СѓР№С‚Рµ РµС‰С‘ СЂР°Р·:")
        return ASKING_NAME
    
    if not re.match(r'^[a-zA-ZР°-СЏРђ-РЇС‘РЃ\s]+$', name):
        await update.message.reply_text("? РРјСЏ РјРѕР¶РµС‚ СЃРѕРґРµСЂР¶Р°С‚СЊ С‚РѕР»СЊРєРѕ Р±СѓРєРІС‹ Рё РїСЂРѕР±РµР»С‹. РџРѕРїСЂРѕР±СѓР№С‚Рµ РµС‰С‘ СЂР°Р·:")
        return ASKING_NAME
    
    context.user_data['temp_name'] = name
    await update.message.reply_text(
        f"? РџСЂРёСЏС‚РЅРѕ РїРѕР·РЅР°РєРѕРјРёС‚СЊСЃСЏ, {name}!\n\n"
        "?? РўРµРїРµСЂСЊ РЅР°РїРёС€РёС‚Рµ РІР°С€Сѓ РґР°С‚Сѓ СЂРѕР¶РґРµРЅРёСЏ РІ С„РѕСЂРјР°С‚Рµ:\n"
        "?? Р”Р”.РњРњ.Р“Р“Р“Р“ (РЅР°РїСЂРёРјРµСЂ: 15.08.1990)"
    )
    return ASKING_BIRTHDATE

async def ask_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    birthdate = update.message.text.strip()
    
    if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', birthdate):
        await update.message.reply_text(
            "? РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ РґР°С‚С‹.\n"
            "?? РџРѕР¶Р°Р»СѓР№СЃС‚Р°, РЅР°РїРёС€РёС‚Рµ РІ С„РѕСЂРјР°С‚Рµ Р”Р”.РњРњ.Р“Р“Р“Р“\n"
            "РџСЂРёРјРµСЂ: 15.08.1990"
        )
        return ASKING_BIRTHDATE
    
    try:
        day, month, year = map(int, birthdate.split('.'))
        birth_date = datetime(year, month, day)
        today = datetime.today()
        
        if birth_date > today or year < 1900:
            await update.message.reply_text(
                "? РџСЂРѕРІРµСЂСЊС‚Рµ РґР°С‚Сѓ: РіРѕРґ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїРѕСЃР»Рµ 1900, Р° РґР°С‚Р° вЂ” РЅРµ РІ Р±СѓРґСѓС‰РµРј.\n"
                "?? РџСЂРёРјРµСЂ РїСЂР°РІРёР»СЊРЅРѕР№ РґР°С‚С‹: 15.08.1990"
            )
            return ASKING_BIRTHDATE
            
    except ValueError:
        await update.message.reply_text(
            "? РќРµРІРµСЂРЅР°СЏ РґР°С‚Р°. РЈР±РµРґРёС‚РµСЃСЊ, С‡С‚Рѕ РґР°С‚Р° СЃСѓС‰РµСЃС‚РІСѓРµС‚.\n"
            "?? РџСЂРёРјРµСЂ: 15.08.1990 (Р° РЅРµ 31.02.1990)"
        )
        return ASKING_BIRTHDATE
    
    user_id = update.effective_user.id
    name = context.user_data.get('temp_name', 'РђРЅРѕРЅРёРј')
    save_user_data(user_id, name, birthdate)
    
    if 'temp_name' in context.user_data:
        del context.user_data['temp_name']
    
    balance = get_balance(user_id)
    await update.message.reply_text(
        f"? РћС‚Р»РёС‡РЅРѕ, {name}! Р”Р°РЅРЅС‹Рµ СЃРѕС…СЂР°РЅРµРЅС‹.\n\n"
        f"? Р’Р°С€ Р±Р°Р»Р°РЅСЃ: {balance} СЂР°СЃРєР»Р°РґРѕРІ\n"
        f"?? Р“РѕС‚РѕРІС‹ Рє РїРµСЂРІРѕРјСѓ РіР°РґР°РЅРёСЋ?"
    )
    
    keyboard = [
        [InlineKeyboardButton("?? РљР°СЂС‚Р° РґРЅСЏ (Р±РµСЃРїР»Р°С‚РЅРѕ)", callback_data='daily_card')],
        [InlineKeyboardButton("?? РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')],
        [InlineKeyboardButton(f"?? Р‘Р°Р»Р°РЅСЃ: {balance}", callback_data='balance')],
        [InlineKeyboardButton("?? РџРѕРґРїРёСЃРєР° (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("??? РњРѕРё СЂР°СЃРєР»Р°РґС‹", callback_data='saved_readings')],
        [InlineKeyboardButton("? РџРѕРјРѕС‰СЊ", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("?? Р’С‹Р±РµСЂРёС‚Рµ РґРµР№СЃС‚РІРёРµ:", reply_markup=reply_markup)
    return ConversationHandler.END

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    slots = get_saved_slots(user_id)
    occupied = len(slots)
    free = 3 - occupied
    
    message = f"??? РњРћР РЎРћРҐР РђРќРЃРќРќР«Р• Р РђРЎРљР›РђР”Р« ???\n\n?? Р”РѕСЃС‚СѓРїРЅРѕ СЏС‡РµРµРє РґР»СЏ СЃРѕС…СЂР°РЅРµРЅРёСЏ: {occupied}/3\n"
    if free > 0:
        message += f"? РЎРІРѕР±РѕРґРЅРѕ СЏС‡РµРµРє: {free}\n\n"
    else:
        message += "?? Р’СЃРµ СЏС‡РµР№РєРё Р·Р°РЅСЏС‚С‹.\n\n"
    
    if not slots:
        message += "РЈ РІР°СЃ РїРѕРєР° РЅРµС‚ СЃРѕС…СЂР°РЅС‘РЅРЅС‹С… СЂР°СЃРєР»Р°РґРѕРІ.\nРЎРґРµР»Р°Р№С‚Рµ СЂР°СЃРєР»Р°Рґ Рё РЅР°Р¶РјРёС‚Рµ В«?? РЎРѕС…СЂР°РЅРёС‚СЊВ»!"
        keyboard = [[InlineKeyboardButton("?? РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text=message, reply_markup=reply_markup)
        return
    
    keyboard = []
    for slot_num in sorted(slots.keys()):
        timestamp = slots[slot_num]
        keyboard.append([InlineKeyboardButton(f"?? РЇС‡РµР№РєР° #{slot_num} ({timestamp})", callback_data=f'view_slot_{slot_num}')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "?? РЈРЎР›РћР’РРЇ РћРџР›РђРўР« Р РЎРћР“Р›РђРЎРР• ??\n"
        "\n?? Р’РђР–РќРћ: Р»СЋР±Р°СЏ РѕРїР»Р°С‚Р° РІ СЌС‚РѕРј Р±РѕС‚Рµ СЏРІР»СЏРµС‚СЃСЏ Р”РћР‘Р РћР’РћР›Р¬РќР«Рњ Р”РћРќРђРўРћРњ.\n"
        "Р Р°СЃРєР»Р°РґС‹ РўР°СЂРѕ РїСЂРµРґРѕСЃС‚Р°РІР»СЏСЋС‚СЃСЏ РІ СЂР°Р·РІР»РµРєР°С‚РµР»СЊРЅС‹С… С†РµР»СЏС….\n"
        "РРЅС‚РµСЂРїСЂРµС‚Р°С†РёРё РєР°СЂС‚ РЅРµ СЏРІР»СЏСЋС‚СЃСЏ РїСЂРµРґСЃРєР°Р·Р°РЅРёРµРј Р±СѓРґСѓС‰РµРіРѕ Рё РЅРµ Р·Р°РјРµРЅСЏСЋС‚ РєРѕРЅСЃСѓР»СЊС‚Р°С†РёСЋ СЃРїРµС†РёР°Р»РёСЃС‚Р°.\n"
        "\n? РќР°Р¶РёРјР°СЏ В«РћРїР»Р°С‚РёС‚СЊВ», РІС‹ СЃРѕРіР»Р°С€Р°РµС‚РµСЃСЊ СЃ С‚РµРј, С‡С‚Рѕ:\n"
        "вЂў РћРїР»Р°С‚Р° РґРѕР±СЂРѕРІРѕР»СЊРЅР°СЏ Рё РЅРµРѕР±СЏР·Р°С‚РµР»СЊРЅР°СЏ.\n"
        "вЂў Р Р°СЃРєР»Р°РґС‹ РЅРѕСЃСЏС‚ СЂР°Р·РІР»РµРєР°С‚РµР»СЊРЅС‹Р№ С…Р°СЂР°РєС‚РµСЂ.\n"
        "вЂў Р’С‹ СЃРѕРІРµСЂС€Р°РµС‚Рµ РїР»Р°С‚С‘Р¶ РїРѕ СЃРѕР±СЃС‚РІРµРЅРЅРѕР№ РІРѕР»Рµ Р±РµР· РїСЂРёРЅСѓР¶РґРµРЅРёСЏ.\n"
        "вЂў Р’РѕР·РІСЂР°С‚ СЃСЂРµРґСЃС‚РІ РЅРµ РїСЂРµРґСѓСЃРјРѕС‚СЂРµРЅ (РґРѕР±СЂРѕРІРѕР»СЊРЅС‹Р№ РґРѕРЅР°С‚).\n"
        "\n? РЎРїР°СЃРёР±Рѕ Р·Р° РїРѕРґРґРµСЂР¶РєСѓ РїСЂРѕРµРєС‚Р°! ??"
    )
    await update.message.reply_text(text=message)

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if not user_data or not user_data.get('name'):
        await update.message.reply_text("РЎРЅР°С‡Р°Р»Р° СѓРєР°Р¶РёС‚Рµ РёРјСЏ Рё РґР°С‚Сѓ СЂРѕР¶РґРµРЅРёСЏ С‡РµСЂРµР· /start")
        return
    
    if can_get_daily_card(user_id):
        card = get_random_cards(1)[0]
        card_name, interpretation = card
        reading = format_daily_card(card_name, interpretation, user_data['name'])
        save_daily_card(user_id, card_name, reading)
        
        await update.message.reply_text(text=reading)
        await update.message.reply_text(
            text="?? РљР°СЂС‚Р° РґРЅСЏ РїРѕР»СѓС‡РµРЅР°! Р’РѕР·РІСЂР°С‰Р°Р№С‚РµСЃСЊ Р·Р°РІС‚СЂР° Р·Р° РЅРѕРІРѕР№ РєР°СЂС‚РѕР№.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("?? РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')],
                [InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]
            ])
        )
    else:
        await update.message.reply_text(
            text="?? Р’С‹ СѓР¶Рµ РїРѕР»СѓС‡РёР»Рё РєР°СЂС‚Сѓ РґРЅСЏ СЃРµРіРѕРґРЅСЏ!\nР’РѕР·РІСЂР°С‰Р°Р№С‚РµСЃСЊ Р·Р°РІС‚СЂР° Р·Р° РЅРѕРІРѕР№ РєР°СЂС‚РѕР№ ??",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]
            ])
        )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if not user_data or not user_data.get('name'):
        await update.message.reply_text("РЎРЅР°С‡Р°Р»Р° СѓРєР°Р¶РёС‚Рµ РёРјСЏ Рё РґР°С‚Сѓ СЂРѕР¶РґРµРЅРёСЏ С‡РµСЂРµР· /start")
        return
    
    balance = get_balance(user_id)
    message = (
        f"?? Р’РђРЁ РўР•РљРЈР©РР™ Р‘РђР›РђРќРЎ ??\n"
        f"\n?? Р”РѕСЃС‚СѓРїРЅРѕ СЂР°СЃРєР»Р°РґРѕРІ: {balance}\n"
        f"\n? РљР°Рє РїРѕР»СѓС‡РёС‚СЊ Р±РѕР»СЊС€Рµ СЂР°СЃРєР»Р°РґРѕРІ:\n"
        f"вЂў РџСЂРёРіР»Р°СЃРёС‚Рµ РґСЂСѓРіР° вЂ” +1 СЂР°СЃРєР»Р°Рґ ??\n"
        f"вЂў РџРѕРґРїРёС€РёС‚РµСЃСЊ РЅР° РєР°РЅР°Р» вЂ” +3 СЂР°СЃРєР»Р°РґР° ??\n"
        f"вЂў РљСѓРїРёС‚Рµ РїР°РєРµС‚ СЂР°СЃРєР»Р°РґРѕРІ СЃРѕ СЃРєРёРґРєРѕР№ ??"
    )
    keyboard = [
        [InlineKeyboardButton("?? РљСѓРїРёС‚СЊ СЂР°СЃРєР»Р°РґС‹", callback_data='buy_packs')],
        [InlineKeyboardButton("?? РџСЂРёРіР»Р°СЃРёС‚СЊ РґСЂСѓРіР°", callback_data='referral')],
        [InlineKeyboardButton("?? РџРѕРґРїРёСЃР°С‚СЊСЃСЏ (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "? РџРћРњРћР©Р¬ ?\n"
        "\n? РљРђРљ РџРћР›Р¬Р—РћР’РђРўР¬РЎРЇ Р‘РћРўРћРњ:\n"
        "вЂў ?? РљР°СЂС‚Р° РґРЅСЏ вЂ” Р±РµСЃРїР»Р°С‚РЅРѕРµ РіР°РґР°РЅРёРµ РЅР° СЃРµРіРѕРґРЅСЏ (1 СЂР°Р· РІ РґРµРЅСЊ)\n"
        "вЂў ?? РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ вЂ” РїРѕРґСЂРѕР±РЅС‹Р№ СЂР°СЃРєР»Р°Рґ РёР· 3+ РєР°СЂС‚ (СЃРїРёСЃС‹РІР°РµС‚СЃСЏ СЃ Р±Р°Р»Р°РЅСЃР°)\n"
        "вЂў ?? РЎРѕС…СЂР°РЅРёС‚СЊ СЂР°СЃРєР»Р°Рґ вЂ” СЃРѕС…СЂР°РЅРёС‚Рµ СЂРµР·СѓР»СЊС‚Р°С‚ РІ РѕРґРЅСѓ РёР· 3 СЏС‡РµРµРє\n"
        "\n??? РЎРћРҐР РђРќР•РќРР• Р РђРЎРљР›РђР”РћР’:\n"
        "вЂў РЈ РІР°СЃ РµСЃС‚СЊ 3 СЏС‡РµР№РєРё РґР»СЏ СЃРѕС…СЂР°РЅРµРЅРёСЏ СЂР°СЃРєР»Р°РґРѕРІ.\n"
        "вЂў Р Р°СЃРєР»Р°РґС‹ РќР• СЃРѕС…СЂР°РЅСЏСЋС‚СЃСЏ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё вЂ” С‚РѕР»СЊРєРѕ РїРѕ РІР°С€РµРјСѓ РІС‹Р±РѕСЂСѓ.\n"
        "вЂў Р•СЃР»Рё РІСЃРµ СЏС‡РµР№РєРё Р·Р°РЅСЏС‚С‹ вЂ” СЃРЅР°С‡Р°Р»Р° СѓРґР°Р»РёС‚Рµ СЃС‚Р°СЂС‹Р№ СЂР°СЃРєР»Р°Рґ.\n"
        "\n?? Р‘РђР›РђРќРЎ:\n"
        "вЂў РџСЂРё СЂРµРіРёСЃС‚СЂР°С†РёРё: 1 Р±РµСЃРїР»Р°С‚РЅС‹Р№ СЂР°СЃРєР»Р°Рґ.\n"
        "вЂў ?? РљР°СЂС‚Р° РґРЅСЏ вЂ” РІСЃРµРіРґР° Р±РµСЃРїР»Р°С‚РЅРѕ, 1 СЂР°Р· РІ РґРµРЅСЊ.\n"
        "вЂў Р—Р° РґСЂСѓРіР°: +1 СЂР°СЃРєР»Р°Рґ.\n"
        "вЂў Р—Р° РїРѕРґРїРёСЃРєСѓ: +3 СЂР°СЃРєР»Р°РґР°.\n"
        "вЂў РџРѕРєСѓРїРєР° РїР°РєРµС‚РѕРІ СЃРѕ СЃРєРёРґРєРѕР№ РґРѕ 15%.\n"
        "\n?? РћРџР›РђРўРђ:\n"
        "вЂў Р‘Р°РЅРєРѕРІСЃРєР°СЏ РєР°СЂС‚Р° вЂ” СЂСѓС‡РЅР°СЏ РїСЂРѕРІРµСЂРєР° СЃРєСЂРёРЅС€РѕС‚Р° ?\n"
        "вЂў РљСЂРёРїС‚РѕРІР°Р»СЋС‚Р° вЂ” РІ СЂР°Р·СЂР°Р±РѕС‚РєРµ ??\n"
        "вЂў РџРѕРґСЂРѕР±РЅРµРµ РѕР± СѓСЃР»РѕРІРёСЏС…: /terms"
    )
    keyboard = [[InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def process_spread_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    spread_id = query.data.replace('spread_', '')
    
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name'):
        await query.message.reply_text("РЎРЅР°С‡Р°Р»Р° СѓРєР°Р¶РёС‚Рµ РёРјСЏ Рё РґР°С‚Сѓ СЂРѕР¶РґРµРЅРёСЏ С‡РµСЂРµР· /start")
        return
    
    balance = get_balance(user_id)
    if balance <= 0:
        await query.edit_message_text(text="? РЈ РІР°СЃ РЅРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ СЂР°СЃРєР»Р°РґРѕРІ. РџРѕРїРѕР»РЅРёС‚Рµ Р±Р°Р»Р°РЅСЃ!")
        return
    
    if not decrease_balance(user_id, 1):
        await query.edit_message_text(text="? РћС€РёР±РєР° РїСЂРё СЃРїРёСЃР°РЅРёРё СЂР°СЃРєР»Р°РґР°. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРѕР·Р¶Рµ.")
        return
    
    new_balance = get_balance(user_id)
    spreads = get_spread_options()
    
    if spread_id not in spreads:
        await query.edit_message_text(text=f"? РќРµРІРµСЂРЅС‹Р№ С‚РёРї СЂР°СЃРєР»Р°РґР°: '{spread_id}'")
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
    keyboard = [[InlineKeyboardButton("?? Р”Р°Р»РµРµ", callback_data='reading_step_1')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=intro_text, reply_markup=reply_markup)
    return READING_INTRO

async def reading_step_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    reading_data = context.user_data.get('current_reading', {})
    if not reading_data:
        await query.edit_message_text(text="? РћС€РёР±РєР°: РґР°РЅРЅС‹Рµ СЂР°СЃРєР»Р°РґР° СѓС‚РµСЂСЏРЅС‹. РќР°С‡РЅРёС‚Рµ Р·Р°РЅРѕРІРѕ.")
        return
    
    cards_text = format_reading_cards(
        reading_data['cards'],
        reading_data['user_name'],
        reading_data['positions'],
        reading_data['spread_id']
    )
    
    keyboard = [
        [InlineKeyboardButton("?? РќР°Р·Р°Рґ", callback_data='back_to_spread_choice')],
        [InlineKeyboardButton("?? Р”Р°Р»РµРµ", callback_data='reading_step_2')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=cards_text, reply_markup=reply_markup)
    return READING_CARDS

async def reading_step_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    reading_data = context.user_data.get('current_reading', {})
    if not reading_data:
        await query.edit_message_text(text="? РћС€РёР±РєР°: РґР°РЅРЅС‹Рµ СЂР°СЃРєР»Р°РґР° СѓС‚РµСЂСЏРЅС‹. РќР°С‡РЅРёС‚Рµ Р·Р°РЅРѕРІРѕ.")
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
        [InlineKeyboardButton("?? РќР°Р·Р°Рґ Рє РєР°СЂС‚Р°Рј", callback_data='back_to_cards')],
        [InlineKeyboardButton("?? РЎРѕС…СЂР°РЅРёС‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='save_last_reading')],
        [InlineKeyboardButton("?? Р•С‰С‘ РѕРґРёРЅ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')],
        [InlineKeyboardButton(f"?? Р‘Р°Р»Р°РЅСЃ: {reading_data['balance_after']}", callback_data='balance')],
        [InlineKeyboardButton("?? Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ", callback_data='back_to_menu')]
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
            await query.message.reply_text("РЎРЅР°С‡Р°Р»Р° СѓРєР°Р¶РёС‚Рµ РёРјСЏ Рё РґР°С‚Сѓ СЂРѕР¶РґРµРЅРёСЏ С‡РµСЂРµР· /start")
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
                text="?? РљР°СЂС‚Р° РґРЅСЏ РїРѕР»СѓС‡РµРЅР°! Р’РѕР·РІСЂР°С‰Р°Р№С‚РµСЃСЊ Р·Р°РІС‚СЂР° Р·Р° РЅРѕРІРѕР№ РєР°СЂС‚РѕР№.\n\n?? РҐРѕС‚РёС‚Рµ СЃРґРµР»Р°С‚СЊ РїРѕРґСЂРѕР±РЅС‹Р№ СЂР°СЃРєР»Р°Рґ? РќР°Р¶РјРёС‚Рµ В«?? РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°РґВ»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("?? РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')],
                    [InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]
                ])
            )
        else:
            await query.edit_message_text(
                text="?? Р’С‹ СѓР¶Рµ РїРѕР»СѓС‡РёР»Рё РєР°СЂС‚Сѓ РґРЅСЏ СЃРµРіРѕРґРЅСЏ!\nР’РѕР·РІСЂР°С‰Р°Р№С‚РµСЃСЊ Р·Р°РІС‚СЂР° Р·Р° РЅРѕРІРѕР№ РєР°СЂС‚РѕР№ ??",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]
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
            "? Р”Р»СЏ РЅР°С‡Р°Р»Р° РіР°РґР°РЅРёСЏ РјРЅРµ РЅСѓР¶РЅС‹ РІР°С€Рё РґР°РЅРЅС‹Рµ:\n"
            "1. РРјСЏ\n"
            "2. Р”Р°С‚Р° СЂРѕР¶РґРµРЅРёСЏ (Р”Р”.РњРњ.Р“Р“Р“Р“)\n\n"
            "РќР°РїРёС€РёС‚Рµ СЃРІРѕС‘ РёРјСЏ:"
        )
        return
    
    if query.data == 'save_last_reading':
        if 'pending_readings' in context.user_data and user_id in context.user_data.get('pending_readings', {}):
            cards, reading_text = context.user_data['pending_readings'][user_id]
            slots = get_saved_slots(user_id)
            free_slots = [i for i in range(1, 4) if i not in slots]
            
            if free_slots:
                slot = save_reading(user_id, cards, reading_text, free_slots[0])
                message = f"? Р Р°СЃРєР»Р°Рґ СЃРѕС…СЂР°РЅС‘РЅ РІ СЏС‡РµР№РєСѓ #{slot}!"
                keyboard = [[InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text=message, reply_markup=reply_markup)
                del context.user_data['pending_readings'][user_id]
            else:
                message = "?? Р’СЃРµ 3 СЏС‡РµР№РєРё Р·Р°РЅСЏС‚С‹. РЎРЅР°С‡Р°Р»Р° СѓРґР°Р»РёС‚Рµ СЃС‚Р°СЂС‹Р№ СЂР°СЃРєР»Р°Рґ:"
                keyboard = []
                for slot_num, timestamp in slots.items():
                    keyboard.append([InlineKeyboardButton(f"? РЇС‡РµР№РєР° #{slot_num} ({timestamp})", callback_data=f'delete_slot_{slot_num}')])
                keyboard.append([InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text=message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="? РќРµС‚ СЂР°СЃРєР»Р°РґР° РґР»СЏ СЃРѕС…СЂР°РЅРµРЅРёСЏ. РЎРЅР°С‡Р°Р»Р° СЃРґРµР»Р°Р№С‚Рµ СЂР°СЃРєР»Р°Рґ!")
    
    elif query.data.startswith('delete_slot_'):
        slot_num = int(query.data.split('_')[2])
        if delete_saved_reading(user_id, slot_num):
            message = f"? Р Р°СЃРєР»Р°Рґ РёР· СЏС‡РµР№РєРё #{slot_num} СѓРґР°Р»С‘РЅ."
        else:
            message = "? РћС€РёР±РєР° СѓРґР°Р»РµРЅРёСЏ."
        keyboard = [[InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'saved_readings':
        slots = get_saved_slots(user_id)
        occupied = len(slots)
        free = 3 - occupied
        
        message = f"??? РњРћР РЎРћРҐР РђРќРЃРќРќР«Р• Р РђРЎРљР›РђР”Р« ???\n?? Р”РѕСЃС‚СѓРїРЅРѕ СЏС‡РµРµРє РґР»СЏ СЃРѕС…СЂР°РЅРµРЅРёСЏ: {occupied}/3\n"
        if free > 0:
            message += f"? РЎРІРѕР±РѕРґРЅРѕ СЏС‡РµРµРє: {free}\n\n"
        else:
            message += "?? Р’СЃРµ СЏС‡РµР№РєРё Р·Р°РЅСЏС‚С‹. Р§С‚РѕР±С‹ СЃРѕС…СЂР°РЅРёС‚СЊ РЅРѕРІС‹Р№ СЂР°СЃРєР»Р°Рґ, СЃРЅР°С‡Р°Р»Р° СѓРґР°Р»РёС‚Рµ СЃС‚Р°СЂС‹Р№.\n\n"
        
        if not slots:
            message += "РЈ РІР°СЃ РїРѕРєР° РЅРµС‚ СЃРѕС…СЂР°РЅС‘РЅРЅС‹С… СЂР°СЃРєР»Р°РґРѕРІ.\nРЎРґРµР»Р°Р№С‚Рµ СЂР°СЃРєР»Р°Рґ Рё РЅР°Р¶РјРёС‚Рµ В«?? РЎРѕС…СЂР°РЅРёС‚СЊВ»!"
            keyboard = [[InlineKeyboardButton("?? РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')], [InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=message, reply_markup=reply_markup)
            return
        
        keyboard = []
        for slot_num in sorted(slots.keys()):
            timestamp = slots[slot_num]
            keyboard.append([InlineKeyboardButton(f"?? РЇС‡РµР№РєР° #{slot_num} ({timestamp})", callback_data=f'view_slot_{slot_num}')])
        keyboard.append([InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data.startswith('view_slot_'):
        slot_num = int(query.data.split('_')[2])
        reading = get_saved_reading(user_id, slot_num)
        if reading:
            cards_str, interpretation, timestamp = reading
            message = f"?? Р РђРЎРљР›РђР” РР— РЇР§Р•Р™РљР #{slot_num}\n?? {timestamp[:16]}\n\n{interpretation}"
            keyboard = [[InlineKeyboardButton("? РЈРґР°Р»РёС‚СЊ СЌС‚РѕС‚ СЂР°СЃРєР»Р°Рґ", callback_data=f'delete_slot_{slot_num}')], [InlineKeyboardButton("?? РќР°Р·Р°Рґ Рє СЃРїРёСЃРєСѓ", callback_data='saved_readings')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="? Р Р°СЃРєР»Р°Рґ РЅРµ РЅР°Р№РґРµРЅ.")
    
    elif query.data == 'balance':
        balance = get_balance(user_id)
        message = (
            f"?? Р’РђРЁ РўР•РљРЈР©РР™ Р‘РђР›РђРќРЎ ??\n"
            f"\n?? Р”РѕСЃС‚СѓРїРЅРѕ СЂР°СЃРєР»Р°РґРѕРІ: {balance}\n"
            f"\n? РљР°Рє РїРѕР»СѓС‡РёС‚СЊ Р±РѕР»СЊС€Рµ СЂР°СЃРєР»Р°РґРѕРІ:\n"
            f"вЂў РџСЂРёРіР»Р°СЃРёС‚Рµ РґСЂСѓРіР° вЂ” +1 СЂР°СЃРєР»Р°Рґ ??\n"
            f"вЂў РџРѕРґРїРёС€РёС‚РµСЃСЊ РЅР° РєР°РЅР°Р» вЂ” +3 СЂР°СЃРєР»Р°РґР° ??\n"
            f"вЂў РљСѓРїРёС‚Рµ РїР°РєРµС‚ СЂР°СЃРєР»Р°РґРѕРІ СЃРѕ СЃРєРёРґРєРѕР№ ??"
        )
        keyboard = [
            [InlineKeyboardButton("?? РљСѓРїРёС‚СЊ СЂР°СЃРєР»Р°РґС‹", callback_data='buy_packs')],
            [InlineKeyboardButton("?? РџСЂРёРіР»Р°СЃРёС‚СЊ РґСЂСѓРіР°", callback_data='referral')],
            [InlineKeyboardButton("?? РџРѕРґРїРёСЃР°С‚СЊСЃСЏ (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'referral':
        ref_link = f"https://t.me/cardnotlie_bot?start={user_id}"
        referral_count = get_referral_count(user_id)
        message = (
            f"?? Р Р•Р¤Р•Р РђР›Р¬РќРђРЇ РџР РћР“Р РђРњРњРђ ??\n\n"
            f"? Р’Р°С€Р° СЂРµС„РµСЂР°Р»СЊРЅР°СЏ СЃСЃС‹Р»РєР°:\n"
            f"{ref_link}\n\n"
            f"?? РџСЂРёРіР»Р°С€РµРЅРѕ РґСЂСѓР·РµР№: {referral_count}\n"
            f"?? Р—Р° РєР°Р¶РґРѕРіРѕ РґСЂСѓРіР° вЂ” +1 Р±РµСЃРїР»Р°С‚РЅС‹Р№ СЂР°СЃРєР»Р°Рґ!\n\n"
            f"?? РџСЂРѕСЃС‚Рѕ РѕС‚РїСЂР°РІСЊС‚Рµ СЃСЃС‹Р»РєСѓ РґСЂСѓР·СЊСЏРј РёР»Рё РІ СЃРѕС†СЃРµС‚Рё!"
        )
        keyboard = [[InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'buy_packs':
        message = (
            "?? РЎРџРћРЎРћР‘Р« РћРџР›РђРўР« ??\n"
            "\nР’С‹Р±РµСЂРёС‚Рµ СѓРґРѕР±РЅС‹Р№ СЃРїРѕСЃРѕР±:\n"
            "\n?? Р‘Р°РЅРєРѕРІСЃРєР°СЏ РєР°СЂС‚Р° вЂ” С‚СЂРµР±СѓРµС‚СЃСЏ СЂСѓС‡РЅР°СЏ РїСЂРѕРІРµСЂРєР° СЃРєСЂРёРЅС€РѕС‚Р° ?\n"
            "?? РљСЂРёРїС‚РѕРІР°Р»СЋС‚Р° вЂ” РІ СЂР°Р·СЂР°Р±РѕС‚РєРµ ??"
        )
        keyboard = [
            [InlineKeyboardButton("?? Р‘Р°РЅРєРѕРІСЃРєР°СЏ РєР°СЂС‚Р°", callback_data='card_packs')],
            [InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'card_packs':
        message = (
            "?? РџРђРљР•РўР« Р РђРЎРљР›РђР”РћР’ ??\n"
            "\n? Р’С‹Р±РµСЂРёС‚Рµ РїР°РєРµС‚ СЃРѕ СЃРєРёРґРєРѕР№:\n"
            "\n?? 1 СЂР°СЃРєР»Р°Рґ вЂ” 100 ?\n"
            "   РРґРµР°Р»СЊРЅРѕ РґР»СЏ СЂР°Р·РѕРІРѕРіРѕ РіР°РґР°РЅРёСЏ.\n"
            "\n?? 3 СЂР°СЃРєР»Р°РґР° вЂ” 285 ? (-5%)\n"
            "   Р­РєРѕРЅРѕРјРёСЏ 15 ?.\n"
            "\n?? 7 СЂР°СЃРєР»Р°РґРѕРІ вЂ” 630 ? (-10%)\n"
            "   Р­РєРѕРЅРѕРјРёСЏ 70 ?.\n"
            "\n?? 13 СЂР°СЃРєР»Р°РґРѕРІ вЂ” 1 105 ? (-15%)\n"
            "   Р­РєРѕРЅРѕРјРёСЏ 195 ?."
        )
        keyboard = [
            [InlineKeyboardButton("1 СЂР°СЃРєР»Р°Рґ вЂ” 100?", callback_data='buy_1')],
            [InlineKeyboardButton("3 СЂР°СЃРєР»Р°РґР° вЂ” 285? (-5%)", callback_data='buy_3')],
            [InlineKeyboardButton("7 СЂР°СЃРєР»Р°РґРѕРІ вЂ” 630? (-10%)", callback_data='buy_7')],
            [InlineKeyboardButton("13 СЂР°СЃРєР»Р°РґРѕРІ вЂ” 1 105? (-15%)", callback_data='buy_13')],
            [InlineKeyboardButton("?? РќР°Р·Р°Рґ", callback_data='buy_packs')]
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
            f"?? РћРџР›РђРўРђ РџРђРљР•РўРђ: {pack_size} СЂР°СЃРєР»Р°РґРѕРІ ??\n"
            f"\n?? РЎС‚РѕРёРјРѕСЃС‚СЊ: {price} ? (СЃРєРёРґРєР° {discount})\n"
            f"\n?? Р РµРєРІРёР·РёС‚С‹ РґР»СЏ РѕРїР»Р°С‚С‹:\n"
            f"?? Р‘Р°РЅРє: Р Р°Р№С„С„Р°Р№Р·РµРЅР±Р°РЅРє.\n"
            f"?? РќРѕРјРµСЂ РєР°СЂС‚С‹: \n"
            f"?? РџРѕР»СѓС‡Р°С‚РµР»СЊ: РЎРµСЂРіРµР№ Р›.\n"
            f"?? РЎСѓРјРјР°: {price} ?.\n"
            f"\n? РџРћРЎР›Р• РћРџР›РђРўР«:\n"
            f"1. РЎРґРµР»Р°Р№С‚Рµ СЃРєСЂРёРЅС€РѕС‚ РїРµСЂРµРІРѕРґР°.\n"
            f"2. РќР°РїРёС€РёС‚Рµ РІ РїРѕРґРґРµСЂР¶РєСѓ @jobphone_admin СЃ РїРѕРјРµС‚РєРѕР№ В«РћРџР›РђРўРђВ».\n"
            f"3. РњС‹ РЅР°С‡РёСЃР»РёРј {pack_size} СЂР°СЃРєР»Р°РґРѕРІ РЅР° РІР°С€ Р±Р°Р»Р°РЅСЃ РІ С‚РµС‡РµРЅРёРµ 10 РјРёРЅСѓС‚! ?\n"
            f"\n?? РџРѕРґСЂРѕР±РЅРµРµ РѕР± СѓСЃР»РѕРІРёСЏС… РѕРїР»Р°С‚С‹: /terms"
        )
        keyboard = [
            [InlineKeyboardButton("?? РќР°Р·Р°Рґ Рє РїР°РєРµС‚Р°Рј", callback_data='card_packs')],
            [InlineKeyboardButton("?? РЈСЃР»РѕРІРёСЏ РѕРїР»Р°С‚С‹", callback_data='terms')],
            [InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'terms' or query.data == 'terms_button':
        message = (
            "?? РЈРЎР›РћР’РРЇ РћРџР›РђРўР« Р РЎРћР“Р›РђРЎРР• ??\n"
            "\n?? Р’РђР–РќРћ: Р»СЋР±Р°СЏ РѕРїР»Р°С‚Р° РІ СЌС‚РѕРј Р±РѕС‚Рµ СЏРІР»СЏРµС‚СЃСЏ Р”РћР‘Р РћР’РћР›Р¬РќР«Рњ Р”РћРќРђРўРћРњ.\n"
            "Р Р°СЃРєР»Р°РґС‹ РўР°СЂРѕ РїСЂРµРґРѕСЃС‚Р°РІР»СЏСЋС‚СЃСЏ РІ СЂР°Р·РІР»РµРєР°С‚РµР»СЊРЅС‹С… С†РµР»СЏС….\n"
            "РРЅС‚РµСЂРїСЂРµС‚Р°С†РёРё РєР°СЂС‚ РЅРµ СЏРІР»СЏСЋС‚СЃСЏ РїСЂРµРґСЃРєР°Р·Р°РЅРёРµРј Р±СѓРґСѓС‰РµРіРѕ Рё РЅРµ Р·Р°РјРµРЅСЏСЋС‚ РєРѕРЅСЃСѓР»СЊС‚Р°С†РёСЋ СЃРїРµС†РёР°Р»РёСЃС‚Р°.\n"
            "\n? РќР°Р¶РёРјР°СЏ В«РћРїР»Р°С‚РёС‚СЊВ», РІС‹ СЃРѕРіР»Р°С€Р°РµС‚РµСЃСЊ СЃ С‚РµРј, С‡С‚Рѕ:\n"
            "вЂў РћРїР»Р°С‚Р° РґРѕР±СЂРѕРІРѕР»СЊРЅР°СЏ Рё РЅРµРѕР±СЏР·Р°С‚РµР»СЊРЅР°СЏ.\n"
            "вЂў Р Р°СЃРєР»Р°РґС‹ РЅРѕСЃСЏС‚ СЂР°Р·РІР»РµРєР°С‚РµР»СЊРЅС‹Р№ С…Р°СЂР°РєС‚РµСЂ.\n"
            "вЂў Р’С‹ СЃРѕРІРµСЂС€Р°РµС‚Рµ РїР»Р°С‚С‘Р¶ РїРѕ СЃРѕР±СЃС‚РІРµРЅРЅРѕР№ РІРѕР»Рµ Р±РµР· РїСЂРёРЅСѓР¶РґРµРЅРёСЏ.\n"
            "вЂў Р’РѕР·РІСЂР°С‚ СЃСЂРµРґСЃС‚РІ РЅРµ РїСЂРµРґСѓСЃРјРѕС‚СЂРµРЅ (РґРѕР±СЂРѕРІРѕР»СЊРЅС‹Р№ РґРѕРЅР°С‚).\n"
            "\n? РЎРїР°СЃРёР±Рѕ Р·Р° РїРѕРґРґРµСЂР¶РєСѓ РїСЂРѕРµРєС‚Р°! ??"
        )
        keyboard = [[InlineKeyboardButton("?? РќР°Р·Р°Рґ Рє РѕРїР»Р°С‚Рµ", callback_data='buy_packs')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'subscribe':
        subscribed = check_subscribed(user_id)
        if subscribed:
            message = "? Р’С‹ СѓР¶Рµ РїРѕРґРїРёСЃР°РЅС‹ РЅР° РЅР°С€ РєР°РЅР°Р»!\n?? Р‘РѕРЅСѓСЃ +3 СЂР°СЃРєР»Р°РґР° СѓР¶Рµ РЅР°С‡РёСЃР»РµРЅ."
        else:
            message = (
                "?? РџРћР”РџРРЎРљРђ РќРђ РљРђРќРђР› ??\n"
                "\nРџРѕРґРїРёС€РёС‚РµСЃСЊ РЅР° РЅР°С€ СЌР·РѕС‚РµСЂРёС‡РµСЃРєРёР№ РєР°РЅР°Р» Рё РїРѕР»СѓС‡РёС‚Рµ +3 Р±РµСЃРїР»Р°С‚РЅС‹С… СЂР°СЃРєР»Р°РґР°!\n"
                "\n? РљР°РЅР°Р»: https://t.me/+5q7VJBPU4_QyMDky\n"
                "\nРџРѕСЃР»Рµ РїРѕРґРїРёСЃРєРё РЅР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ РЅРёР¶Рµ:"
            )
        keyboard = [
            [InlineKeyboardButton("?? РџРµСЂРµР№С‚Рё РІ РєР°РЅР°Р»", url="https://t.me/+5q7VJBPU4_QyMDky")],
            [InlineKeyboardButton("? РЇ РїРѕРґРїРёСЃР°Р»СЃСЏ (+3 СЂР°СЃРєР»Р°РґР°)", callback_data='confirm_subscribe')],
            [InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'confirm_subscribe':
        subscribed_db = check_subscribed(user_id)
        
        if subscribed_db:
            message = "? Р’С‹ СѓР¶Рµ РїРѕР»СѓС‡РёР»Рё Р±РѕРЅСѓСЃ Р·Р° РїРѕРґРїРёСЃРєСѓ!"
        else:
            try:
                chat_member = await context.bot.get_chat_member(
                    chat_id="@+5q7VJBPU4_QyMDky",
                    user_id=user_id
                )
                if chat_member.status in ["member", "administrator", "creator"]:
                    mark_subscribed(user_id)
                    message = "?? РЈСЂР°! Р’С‹ РїРѕРґРїРёСЃР°Р»РёСЃСЊ РЅР° РєР°РЅР°Р»!\n? Р‘РѕРЅСѓСЃ +3 Р±РµСЃРїР»Р°С‚РЅС‹С… СЂР°СЃРєР»Р°РґР° РЅР°С‡РёСЃР»РµРЅ РЅР° РІР°С€ СЃС‡С‘С‚!"
                else:
                    message = "? Р’С‹ РЅРµ РїРѕРґРїРёСЃР°РЅС‹ РЅР° РєР°РЅР°Р».\nРџРѕР¶Р°Р»СѓР№СЃС‚Р°, РїРѕРґРїРёС€РёС‚РµСЃСЊ Рё РЅР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ СЃРЅРѕРІР°."
            except Exception as e:
                print(f"РћС€РёР±РєР° РїСЂРѕРІРµСЂРєРё РїРѕРґРїРёСЃРєРё: {e}")
                message = "? РќРµ СѓРґР°Р»РѕСЃСЊ РїСЂРѕРІРµСЂРёС‚СЊ РїРѕРґРїРёСЃРєСѓ. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРѕР·Р¶Рµ."
        
        keyboard = [[InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'help':
        message = (
            "? РџРћРњРћР©Р¬ ?\n"
            "\n? РљРђРљ РџРћР›Р¬Р—РћР’РђРўР¬РЎРЇ Р‘РћРўРћРњ:\n"
            "вЂў ?? РљР°СЂС‚Р° РґРЅСЏ вЂ” Р±РµСЃРїР»Р°С‚РЅРѕРµ РіР°РґР°РЅРёРµ РЅР° СЃРµРіРѕРґРЅСЏ (1 СЂР°Р· РІ РґРµРЅСЊ)\n"
            "вЂў ?? РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ вЂ” РїРѕРґСЂРѕР±РЅС‹Р№ СЂР°СЃРєР»Р°Рґ РёР· 3+ РєР°СЂС‚ (СЃРїРёСЃС‹РІР°РµС‚СЃСЏ СЃ Р±Р°Р»Р°РЅСЃР°)\n"
            "вЂў ?? РЎРѕС…СЂР°РЅРёС‚СЊ СЂР°СЃРєР»Р°Рґ вЂ” СЃРѕС…СЂР°РЅРёС‚Рµ СЂРµР·СѓР»СЊС‚Р°С‚ РІ РѕРґРЅСѓ РёР· 3 СЏС‡РµРµРє\n"
            "\n??? РЎРћРҐР РђРќР•РќРР• Р РђРЎРљР›РђР”РћР’:\n"
            "вЂў РЈ РІР°СЃ РµСЃС‚СЊ 3 СЏС‡РµР№РєРё РґР»СЏ СЃРѕС…СЂР°РЅРµРЅРёСЏ СЂР°СЃРєР»Р°РґРѕРІ.\n"
            "вЂў Р Р°СЃРєР»Р°РґС‹ РќР• СЃРѕС…СЂР°РЅСЏСЋС‚СЃСЏ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё вЂ” С‚РѕР»СЊРєРѕ РїРѕ РІР°С€РµРјСѓ РІС‹Р±РѕСЂСѓ.\n"
            "вЂў Р•СЃР»Рё РІСЃРµ СЏС‡РµР№РєРё Р·Р°РЅСЏС‚С‹ вЂ” СЃРЅР°С‡Р°Р»Р° СѓРґР°Р»РёС‚Рµ СЃС‚Р°СЂС‹Р№ СЂР°СЃРєР»Р°Рґ.\n"
            "\n?? Р‘РђР›РђРќРЎ:\n"
            "вЂў РџСЂРё СЂРµРіРёСЃС‚СЂР°С†РёРё: 1 Р±РµСЃРїР»Р°С‚РЅС‹Р№ СЂР°СЃРєР»Р°Рґ.\n"
            "вЂў ?? РљР°СЂС‚Р° РґРЅСЏ вЂ” РІСЃРµРіРґР° Р±РµСЃРїР»Р°С‚РЅРѕ, 1 СЂР°Р· РІ РґРµРЅСЊ.\n"
            "вЂў Р—Р° РґСЂСѓРіР°: +1 СЂР°СЃРєР»Р°Рґ.\n"
            "вЂў Р—Р° РїРѕРґРїРёСЃРєСѓ: +3 СЂР°СЃРєР»Р°РґР°.\n"
            "вЂў РџРѕРєСѓРїРєР° РїР°РєРµС‚РѕРІ СЃРѕ СЃРєРёРґРєРѕР№ РґРѕ 15%.\n"
            "\n?? РћРџР›РђРўРђ:\n"
            "вЂў Р‘Р°РЅРєРѕРІСЃРєР°СЏ РєР°СЂС‚Р° вЂ” СЂСѓС‡РЅР°СЏ РїСЂРѕРІРµСЂРєР° СЃРєСЂРёРЅС€РѕС‚Р° ?\n"
            "вЂў РљСЂРёРїС‚РѕРІР°Р»СЋС‚Р° вЂ” РІ СЂР°Р·СЂР°Р±РѕС‚РєРµ ??\n"
            "вЂў РџРѕРґСЂРѕР±РЅРµРµ РѕР± СѓСЃР»РѕРІРёСЏС…: /terms"
        )
        keyboard = [[InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'back_to_menu':
        user_data = get_user_data(user_id)
        if not user_data or not user_data.get('name'):
            await query.message.reply_text("РќР°РїРёС€РёС‚Рµ СЃРІРѕС‘ РёРјСЏ:")
            return
        
        balance = get_balance(user_id)
        message = f"?? Р”РћР‘Р Рћ РџРћР–РђР›РћР’РђРўР¬ Р’ РњРР  РўРђР Рћ! ??\n? {user_data['name']}, РІР°С€ Р±Р°Р»Р°РЅСЃ: {balance} СЂР°СЃРєР»Р°РґРѕРІ"
        keyboard = [
            [InlineKeyboardButton("?? РљР°СЂС‚Р° РґРЅСЏ (Р±РµСЃРїР»Р°С‚РЅРѕ)", callback_data='daily_card')],
            [InlineKeyboardButton("?? РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')],
            [InlineKeyboardButton(f"?? Р‘Р°Р»Р°РЅСЃ: {balance}", callback_data='balance')],
            [InlineKeyboardButton("?? РџРѕРґРїРёСЃРєР° (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("??? РњРѕРё СЂР°СЃРєР»Р°РґС‹", callback_data='saved_readings')],
            [InlineKeyboardButton("? РџРѕРјРѕС‰СЊ", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)

async def choose_spread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name'):
        await query.message.reply_text("РЎРЅР°С‡Р°Р»Р° СѓРєР°Р¶РёС‚Рµ РёРјСЏ Рё РґР°С‚Сѓ СЂРѕР¶РґРµРЅРёСЏ С‡РµСЂРµР· /start")
        return
    
    balance = get_balance(user_id)
    if balance <= 0:
        keyboard = [
            [InlineKeyboardButton("?? РљСѓРїРёС‚СЊ СЂР°СЃРєР»Р°РґС‹", callback_data='buy_packs')],
            [InlineKeyboardButton("?? РџРѕРґРїРёСЃР°С‚СЊСЃСЏ (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("?? РњРµРЅСЋ", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="?? РЈ РІР°СЃ Р·Р°РєРѕРЅС‡РёР»РёСЃСЊ СЂР°СЃРєР»Р°РґС‹.\n?? РџРѕРїРѕР»РЅРёС‚Рµ Р±Р°Р»Р°РЅСЃ РёР»Рё РїРѕР»СѓС‡РёС‚Рµ Р±РѕРЅСѓСЃС‹!",
            reply_markup=reply_markup
        )
        return
    
    spreads = get_spread_options()
    spreads.pop('daily', None)
    
    message = "?? Р’Р«Р‘Р•Р РРўР• РўРРџ Р РђРЎРљР›РђР”Рђ ??\n\n"
    keyboard = []
    
    for spread_id, spread_info in spreads.items():
        keyboard.append([InlineKeyboardButton(spread_info['name'], callback_data=f'spread_{spread_id}')])
    
    keyboard.append([InlineKeyboardButton("?? РќР°Р·Р°Рґ", callback_data='back_to_menu')])
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
        await update.message.reply_text("РЎРЅР°С‡Р°Р»Р° СѓРєР°Р¶РёС‚Рµ РёРјСЏ Рё РґР°С‚Сѓ СЂРѕР¶РґРµРЅРёСЏ С‡РµСЂРµР· /start")
        return
    
    balance = get_balance(user_id)
    message = f"?? Р”РћР‘Р Рћ РџРћР–РђР›РћР’РђРўР¬ Р’ РњРР  РўРђР Рћ! ??\n? {user_data['name']}, РІР°С€ Р±Р°Р»Р°РЅСЃ: {balance} СЂР°СЃРєР»Р°РґРѕРІ"
    
    keyboard = [
        [InlineKeyboardButton("?? РљР°СЂС‚Р° РґРЅСЏ (Р±РµСЃРїР»Р°С‚РЅРѕ)", callback_data='daily_card')],
        [InlineKeyboardButton("?? РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')],
        [InlineKeyboardButton(f"?? Р‘Р°Р»Р°РЅСЃ: {balance}", callback_data='balance')],
        [InlineKeyboardButton("?? РџРѕРґРїРёСЃРєР° (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("??? РњРѕРё СЂР°СЃРєР»Р°РґС‹", callback_data='saved_readings')],
        [InlineKeyboardButton("? РџРѕРјРѕС‰СЊ", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)
