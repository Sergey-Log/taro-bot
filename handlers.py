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
    format_daily_card
)

ASKING_NAME, ASKING_BIRTHDATE = range(2)

# === РЎРќРђР§РђР›Рђ РћРџР Р•Р”Р•Р›РЇР•Рњ Р’РЎР• Р¤РЈРќРљР¦РР ===

async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)
    
    # РћР±СЂР°Р±РѕС‚РєР° СЂРµС„РµСЂР°Р»СЊРЅРѕР№ СЃСЃС‹Р»РєРё
    if context.args:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user.id:
                if add_referral(referrer_id, user.id):
                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"рџЋ‰ РћС‚Р»РёС‡РЅРѕ! Р’Р°С€ РґСЂСѓРі {user.first_name} РїСЂРёСЃРѕРµРґРёРЅРёР»СЃСЏ!\nР’С‹ РїРѕР»СѓС‡РёР»Рё +1 СЂР°СЃРєР»Р°Рґ Рє Р±Р°Р»Р°РЅСЃСѓ!"
                        )
                    except: pass
        except: pass
    
    user_data = get_user_data(user.id)
    if not user_data or not user_data.get('name') or not user_data.get('birthdate'):
        await update.message.reply_text(
            "вњЁ Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ РІ РјРёСЂ РўР°СЂРѕ!\n\n"
            "рџ”® Р”Р»СЏ РїРµСЂСЃРѕРЅР°Р»РёР·РёСЂРѕРІР°РЅРЅРѕРіРѕ РіР°РґР°РЅРёСЏ РјРЅРµ РЅСѓР¶РЅРѕ СѓР·РЅР°С‚СЊ РІР°СЃ РЅРµРјРЅРѕРіРѕ Р»СѓС‡С€Рµ.\n\n"
            "рџ’« РЎРЅР°С‡Р°Р»Р° РЅР°РїРёС€РёС‚Рµ, РєР°Рє РІР°СЃ Р·РѕРІСѓС‚:"
        )
        return ASKING_NAME
    
    balance = get_balance(user.id)
    message = f"рџ”® Р”РћР‘Р Рћ РџРћР–РђР›РћР’РђРўР¬ Р’ РњРР  РўРђР Рћ! рџ”®\nвњЁ {user_data['name']}, РІР°С€ Р±Р°Р»Р°РЅСЃ: {balance} СЂР°СЃРєР»Р°РґРѕРІ"
    
    keyboard = [
        [InlineKeyboardButton("рџЊ… РљР°СЂС‚Р° РґРЅСЏ (Р±РµСЃРїР»Р°С‚РЅРѕ)", callback_data='daily_card')],
        [InlineKeyboardButton("рџЋґ РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')],
        [InlineKeyboardButton(f"вљ–пёЏ Р‘Р°Р»Р°РЅСЃ: {balance}", callback_data='balance')],
        [InlineKeyboardButton("рџ“є РџРѕРґРїРёСЃРєР° (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("рџ—„пёЏ РњРѕРё СЂР°СЃРєР»Р°РґС‹", callback_data='saved_readings')],
        [InlineKeyboardButton("вќ“ РџРѕРјРѕС‰СЊ", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)
    return ConversationHandler.END

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("вќЊ РРјСЏ РґРѕР»Р¶РЅРѕ Р±С‹С‚СЊ РЅРµ РјРµРЅРµРµ 2 СЃРёРјРІРѕР»РѕРІ. РџРѕРїСЂРѕР±СѓР№С‚Рµ РµС‰С‘ СЂР°Р·:")
        return ASKING_NAME
    
    if not re.match(r'^[Р°-СЏРђ-РЇa-zA-Z\s]+$', name):
        await update.message.reply_text("вќЊ РРјСЏ РјРѕР¶РµС‚ СЃРѕРґРµСЂР¶Р°С‚СЊ С‚РѕР»СЊРєРѕ Р±СѓРєРІС‹ Рё РїСЂРѕР±РµР»С‹. РџРѕРїСЂРѕР±СѓР№С‚Рµ РµС‰С‘ СЂР°Р·:")
        return ASKING_NAME
    
    context.user_data['temp_name'] = name
    await update.message.reply_text(
        f"вњЁ РџСЂРёСЏС‚РЅРѕ РїРѕР·РЅР°РєРѕРјРёС‚СЊСЃСЏ, {name}!\n\n"
        "рџ’« РўРµРїРµСЂСЊ РЅР°РїРёС€РёС‚Рµ РІР°С€Сѓ РґР°С‚Сѓ СЂРѕР¶РґРµРЅРёСЏ РІ С„РѕСЂРјР°С‚Рµ:\n"
        "рџ“… Р”Р”.РњРњ.Р“Р“Р“Р“ (РЅР°РїСЂРёРјРµСЂ: 15.08.1990)"
    )
    return ASKING_BIRTHDATE

async def ask_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    birthdate = update.message.text.strip()
    
    if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', birthdate):
        await update.message.reply_text(
            "вќЊ РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ РґР°С‚С‹.\n"
            "рџ“… РџРѕР¶Р°Р»СѓР№СЃС‚Р°, РЅР°РїРёС€РёС‚Рµ РІ С„РѕСЂРјР°С‚Рµ Р”Р”.РњРњ.Р“Р“Р“Р“\n"
            "РџСЂРёРјРµСЂ: 15.08.1990"
        )
        return ASKING_BIRTHDATE
    
    try:
        day, month, year = map(int, birthdate.split('.'))
        birth_date = datetime(year, month, day)
        today = datetime.today()
        
        if birth_date > today or year < 1900:
            await update.message.reply_text(
                "вќЊ РџСЂРѕРІРµСЂСЊС‚Рµ РґР°С‚Сѓ: РіРѕРґ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ РїРѕСЃР»Рµ 1900, Р° РґР°С‚Р° вЂ” РЅРµ РІ Р±СѓРґСѓС‰РµРј.\n"
                "рџ“… РџСЂРёРјРµСЂ РїСЂР°РІРёР»СЊРЅРѕР№ РґР°С‚С‹: 15.08.1990"
            )
            return ASKING_BIRTHDATE
            
    except ValueError:
        await update.message.reply_text(
            "вќЊ РќРµРІРµСЂРЅР°СЏ РґР°С‚Р°. РЈР±РµРґРёС‚РµСЃСЊ, С‡С‚Рѕ РґР°С‚Р° СЃСѓС‰РµСЃС‚РІСѓРµС‚.\n"
            "рџ“… РџСЂРёРјРµСЂ: 15.08.1990 (Р° РЅРµ 31.02.1990)"
        )
        return ASKING_BIRTHDATE
    
    user_id = update.effective_user.id
    name = context.user_data.get('temp_name', 'РђРЅРѕРЅРёРј')
    save_user_data(user_id, name, birthdate)
    
    if 'temp_name' in context.user_data:
        del context.user_data['temp_name']
    
    balance = get_balance(user_id)
    await update.message.reply_text(
        f"вњ… РћС‚Р»РёС‡РЅРѕ, {name}! Р”Р°РЅРЅС‹Рµ СЃРѕС…СЂР°РЅРµРЅС‹.\n\n"
        f"вњЁ Р’Р°С€ Р±Р°Р»Р°РЅСЃ: {balance} СЂР°СЃРєР»Р°РґРѕРІ\n"
        f"рџЋґ Р“РѕС‚РѕРІС‹ Рє РїРµСЂРІРѕРјСѓ РіР°РґР°РЅРёСЋ?"
    )
    
    keyboard = [
        [InlineKeyboardButton("рџЊ… РљР°СЂС‚Р° РґРЅСЏ (Р±РµСЃРїР»Р°С‚РЅРѕ)", callback_data='daily_card')],
        [InlineKeyboardButton("рџЋґ РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')],
        [InlineKeyboardButton(f"вљ–пёЏ Р‘Р°Р»Р°РЅСЃ: {balance}", callback_data='balance')],
        [InlineKeyboardButton("рџ“є РџРѕРґРїРёСЃРєР° (+3)", callback_data='subscribe')],
        [InlineKeyboardButton("рџ—„пёЏ РњРѕРё СЂР°СЃРєР»Р°РґС‹", callback_data='saved_readings')],
        [InlineKeyboardButton("вќ“ РџРѕРјРѕС‰СЊ", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("рџ”® Р’С‹Р±РµСЂРёС‚Рµ РґРµР№СЃС‚РІРёРµ:", reply_markup=reply_markup)
    return ConversationHandler.END

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    slots = get_saved_slots(user_id)
    occupied = len(slots)
    free = 3 - occupied
    
    message = f"рџ—„пёЏ РњРћР РЎРћРҐР РђРќРЃРќРќР«Р• Р РђРЎРљР›РђР”Р« рџ—„пёЏ\n\nрџ“¦ Р”РѕСЃС‚СѓРїРЅРѕ СЏС‡РµРµРє РґР»СЏ СЃРѕС…СЂР°РЅРµРЅРёСЏ: {occupied}/3\n"
    if free > 0:
        message += f"вњЁ РЎРІРѕР±РѕРґРЅРѕ СЏС‡РµРµРє: {free}\n\n"
    else:
        message += "вљ пёЏ Р’СЃРµ СЏС‡РµР№РєРё Р·Р°РЅСЏС‚С‹.\n\n"
    
    if not slots:
        message += "РЈ РІР°СЃ РїРѕРєР° РЅРµС‚ СЃРѕС…СЂР°РЅС‘РЅРЅС‹С… СЂР°СЃРєР»Р°РґРѕРІ.\nРЎРґРµР»Р°Р№С‚Рµ СЂР°СЃРєР»Р°Рґ Рё РЅР°Р¶РјРёС‚Рµ В«рџ’ѕ РЎРѕС…СЂР°РЅРёС‚СЊВ»!"
        keyboard = [[InlineKeyboardButton("рџЋґ РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text=message, reply_markup=reply_markup)
        return
    
    keyboard = []
    for slot_num in sorted(slots.keys()):
        timestamp = slots[slot_num]
        keyboard.append([InlineKeyboardButton(f"рџ“¦ РЇС‡РµР№РєР° #{slot_num} ({timestamp})", callback_data=f'view_slot_{slot_num}')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text=message, reply_markup=reply_markup)

async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "рџ“„ РЈРЎР›РћР’РРЇ РћРџР›РђРўР« Р РЎРћР“Р›РђРЎРР• рџ“„\n"
        "\nрџ’« Р’РђР–РќРћ: Р»СЋР±Р°СЏ РѕРїР»Р°С‚Р° РІ СЌС‚РѕРј Р±РѕС‚Рµ СЏРІР»СЏРµС‚СЃСЏ Р”РћР‘Р РћР’РћР›Р¬РќР«Рњ Р”РћРќРђРўРћРњ.\n"
        "Р Р°СЃРєР»Р°РґС‹ РўР°СЂРѕ РїСЂРµРґРѕСЃС‚Р°РІР»СЏСЋС‚СЃСЏ РІ СЂР°Р·РІР»РµРєР°С‚РµР»СЊРЅС‹С… С†РµР»СЏС….\n"
        "РРЅС‚РµСЂРїСЂРµС‚Р°С†РёРё РєР°СЂС‚ РЅРµ СЏРІР»СЏСЋС‚СЃСЏ РїСЂРµРґСЃРєР°Р·Р°РЅРёРµРј Р±СѓРґСѓС‰РµРіРѕ Рё РЅРµ Р·Р°РјРµРЅСЏСЋС‚ РєРѕРЅСЃСѓР»СЊС‚Р°С†РёСЋ СЃРїРµС†РёР°Р»РёСЃС‚Р°.\n"
        "\nвњ… РќР°Р¶РёРјР°СЏ В«РћРїР»Р°С‚РёС‚СЊВ», РІС‹ СЃРѕРіР»Р°С€Р°РµС‚РµСЃСЊ СЃ С‚РµРј, С‡С‚Рѕ:\n"
        "вЂў РћРїР»Р°С‚Р° РґРѕР±СЂРѕРІРѕР»СЊРЅР°СЏ Рё РЅРµРѕР±СЏР·Р°С‚РµР»СЊРЅР°СЏ.\n"
        "вЂў Р Р°СЃРєР»Р°РґС‹ РЅРѕСЃСЏС‚ СЂР°Р·РІР»РµРєР°С‚РµР»СЊРЅС‹Р№ С…Р°СЂР°РєС‚РµСЂ.\n"
        "вЂў Р’С‹ СЃРѕРІРµСЂС€Р°РµС‚Рµ РїР»Р°С‚С‘Р¶ РїРѕ СЃРѕР±СЃС‚РІРµРЅРЅРѕР№ РІРѕР»Рµ Р±РµР· РїСЂРёРЅСѓР¶РґРµРЅРёСЏ.\n"
        "вЂў Р’РѕР·РІСЂР°С‚ СЃСЂРµРґСЃС‚РІ РЅРµ РїСЂРµРґСѓСЃРјРѕС‚СЂРµРЅ (РґРѕР±СЂРѕРІРѕР»СЊРЅС‹Р№ РґРѕРЅР°С‚).\n"
        "\nвњЁ РЎРїР°СЃРёР±Рѕ Р·Р° РїРѕРґРґРµСЂР¶РєСѓ РїСЂРѕРµРєС‚Р°! рџ’«"
    )
    await update.message.reply_text(text=message)

# === РўРћР›Р¬РљРћ РџРћРЎР›Р• Р­РўРћР“Рћ РЎРћР—Р”РђРЃРњ start_handler ===

start_handler = ConversationHandler(
    entry_points=[CommandHandler("start", _start)],
    states={
        ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASKING_BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_birthdate)],
    },
    fallbacks=[CommandHandler("start", _start)],
    allow_reentry=True
)

# === РћРЎРўРђР›Р¬РќР«Р• РћР‘Р РђР‘РћРўР§РРљР ===

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # РћР±СЂР°Р±РѕС‚РєР° РєР°СЂС‚С‹ РґРЅСЏ
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
                text="рџЊ… РљР°СЂС‚Р° РґРЅСЏ РїРѕР»СѓС‡РµРЅР°! Р’РѕР·РІСЂР°С‰Р°Р№С‚РµСЃСЊ Р·Р°РІС‚СЂР° Р·Р° РЅРѕРІРѕР№ РєР°СЂС‚РѕР№.\n\nрџ’« РҐРѕС‚РёС‚Рµ СЃРґРµР»Р°С‚СЊ РїРѕРґСЂРѕР±РЅС‹Р№ СЂР°СЃРєР»Р°Рґ? РќР°Р¶РјРёС‚Рµ В«рџЋґ РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°РґВ»",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("рџЋґ РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')],
                    [InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]
                ])
            )
        else:
            existing_card = get_daily_card(user_id)
            if existing_card:
                card_name, interpretation = existing_card
                await query.edit_message_text(
                    text=f"рџЊ… Р’Р« РЈР–Р• РџРћР›РЈР§РР›Р РљРђР РўРЈ Р”РќРЇ РЎР•Р“РћР”РќРЇ!\n\n{interpretation}\n\nрџ’« Р’РµСЂРЅРёС‚РµСЃСЊ Р·Р°РІС‚СЂР° Р·Р° РЅРѕРІРѕР№ РєР°СЂС‚РѕР№ РёР»Рё СЃРґРµР»Р°Р№С‚Рµ РїРѕРґСЂРѕР±РЅС‹Р№ СЂР°СЃРєР»Р°Рґ:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("рџЋґ РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')],
                        [InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]
                    ])
                )
            else:
                await query.edit_message_text(
                    text="рџЊ… Р’С‹ СѓР¶Рµ РїРѕР»СѓС‡РёР»Рё РєР°СЂС‚Сѓ РґРЅСЏ СЃРµРіРѕРґРЅСЏ!\nР’РѕР·РІСЂР°С‰Р°Р№С‚РµСЃСЊ Р·Р°РІС‚СЂР° Р·Р° РЅРѕРІРѕР№ РєР°СЂС‚РѕР№ вЂпёЏ",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]
                    ])
                )
        return
    
    # РћР±СЂР°Р±РѕС‚РєР° РІС‹Р±РѕСЂР° СЂР°СЃРєР»Р°РґР°
    if query.data.startswith('spread_'):
        await process_spread_selection(update, context)
        return
    
    if query.data == 'do_tarot':
        await choose_spread(update, context)
        return
    
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('name') or not user_data.get('birthdate'):
        await query.message.reply_text(
            "вњЁ Р”Р»СЏ РЅР°С‡Р°Р»Р° РіР°РґР°РЅРёСЏ РјРЅРµ РЅСѓР¶РЅС‹ РІР°С€Рё РґР°РЅРЅС‹Рµ:\n"
            "1. РРјСЏ\n"
            "2. Р”Р°С‚Р° СЂРѕР¶РґРµРЅРёСЏ (Р”Р”.РњРњ.Р“Р“Р“Р“)\n\n"
            "РќР°РїРёС€РёС‚Рµ СЃРІРѕС‘ РёРјСЏ:"
        )
        return
    
    # РћР±СЂР°Р±РѕС‚РєР° СЃРѕС…СЂР°РЅРµРЅРёСЏ СЂР°СЃРєР»Р°РґР°
    if query.data == 'save_last_reading':
        if 'pending_readings' in context.user_data and user_id in context.user_data.get('pending_readings', {}):
            cards, reading_text = context.user_data['pending_readings'][user_id]
            slots = get_saved_slots(user_id)
            free_slots = [i for i in range(1, 4) if i not in slots]
            
            if free_slots:
                slot = save_reading(user_id, cards, reading_text, free_slots[0])
                message = f"вњ… Р Р°СЃРєР»Р°Рґ СЃРѕС…СЂР°РЅС‘РЅ РІ СЏС‡РµР№РєСѓ #{slot}!"
                keyboard = [[InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text=message, reply_markup=reply_markup)
                del context.user_data['pending_readings'][user_id]
            else:
                message = "вљ пёЏ Р’СЃРµ 3 СЏС‡РµР№РєРё Р·Р°РЅСЏС‚С‹. РЎРЅР°С‡Р°Р»Р° СѓРґР°Р»РёС‚Рµ СЃС‚Р°СЂС‹Р№ СЂР°СЃРєР»Р°Рґ:"
                keyboard = []
                for slot_num, timestamp in slots.items():
                    keyboard.append([InlineKeyboardButton(f"вќЊ РЇС‡РµР№РєР° #{slot_num} ({timestamp})", callback_data=f'delete_slot_{slot_num}')])
                keyboard.append([InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text=message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="вќЊ РќРµС‚ СЂР°СЃРєР»Р°РґР° РґР»СЏ СЃРѕС…СЂР°РЅРµРЅРёСЏ. РЎРЅР°С‡Р°Р»Р° СЃРґРµР»Р°Р№С‚Рµ СЂР°СЃРєР»Р°Рґ!")
    
    elif query.data.startswith('delete_slot_'):
        slot_num = int(query.data.split('_')[2])
        if delete_saved_reading(user_id, slot_num):
            message = f"вњ… Р Р°СЃРєР»Р°Рґ РёР· СЏС‡РµР№РєРё #{slot_num} СѓРґР°Р»С‘РЅ."
        else:
            message = "вќЊ РћС€РёР±РєР° СѓРґР°Р»РµРЅРёСЏ."
        keyboard = [[InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'saved_readings':
        slots = get_saved_slots(user_id)
        occupied = len(slots)
        free = 3 - occupied
        
        message = f"рџ—„пёЏ РњРћР РЎРћРҐР РђРќРЃРќРќР«Р• Р РђРЎРљР›РђР”Р« рџ—„пёЏ\nрџ“¦ Р”РѕСЃС‚СѓРїРЅРѕ СЏС‡РµРµРє РґР»СЏ СЃРѕС…СЂР°РЅРµРЅРёСЏ: {occupied}/3\n"
        if free > 0:
            message += f"вњЁ РЎРІРѕР±РѕРґРЅРѕ СЏС‡РµРµРє: {free}\n\n"
        else:
            message += "вљ пёЏ Р’СЃРµ СЏС‡РµР№РєРё Р·Р°РЅСЏС‚С‹. Р§С‚РѕР±С‹ СЃРѕС…СЂР°РЅРёС‚СЊ РЅРѕРІС‹Р№ СЂР°СЃРєР»Р°Рґ, СЃРЅР°С‡Р°Р»Р° СѓРґР°Р»РёС‚Рµ СЃС‚Р°СЂС‹Р№.\n\n"
        
        if not slots:
            message += "РЈ РІР°СЃ РїРѕРєР° РЅРµС‚ СЃРѕС…СЂР°РЅС‘РЅРЅС‹С… СЂР°СЃРєР»Р°РґРѕРІ.\nРЎРґРµР»Р°Р№С‚Рµ СЂР°СЃРєР»Р°Рґ Рё РЅР°Р¶РјРёС‚Рµ В«рџ’ѕ РЎРѕС…СЂР°РЅРёС‚СЊВ»!"
            keyboard = [[InlineKeyboardButton("рџЋґ РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')], [InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=message, reply_markup=reply_markup)
            return
        
        keyboard = []
        for slot_num in sorted(slots.keys()):
            timestamp = slots[slot_num]
            keyboard.append([InlineKeyboardButton(f"рџ“¦ РЇС‡РµР№РєР° #{slot_num} ({timestamp})", callback_data=f'view_slot_{slot_num}')])
        keyboard.append([InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data.startswith('view_slot_'):
        slot_num = int(query.data.split('_')[2])
        reading = get_saved_reading(user_id, slot_num)
        if reading:
            cards_str, interpretation, timestamp = reading
            message = f"рџ“¦ Р РђРЎРљР›РђР” РР— РЇР§Р•Р™РљР #{slot_num}\nрџ“… {timestamp[:16]}\n\n{interpretation}"
            keyboard = [[InlineKeyboardButton("вќЊ РЈРґР°Р»РёС‚СЊ СЌС‚РѕС‚ СЂР°СЃРєР»Р°Рґ", callback_data=f'delete_slot_{slot_num}')], [InlineKeyboardButton("в¬…пёЏ РќР°Р·Р°Рґ Рє СЃРїРёСЃРєСѓ", callback_data='saved_readings')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text="вќЊ Р Р°СЃРєР»Р°Рґ РЅРµ РЅР°Р№РґРµРЅ.")
    
    elif query.data == 'balance':
        balance = get_balance(user_id)
        message = (
            f"вљ–пёЏ Р’РђРЁ РўР•РљРЈР©РР™ Р‘РђР›РђРќРЎ вљ–пёЏ\n"
            f"\nрџ”® Р”РѕСЃС‚СѓРїРЅРѕ СЂР°СЃРєР»Р°РґРѕРІ: {balance}\n"
            f"\nвњЁ РљР°Рє РїРѕР»СѓС‡РёС‚СЊ Р±РѕР»СЊС€Рµ СЂР°СЃРєР»Р°РґРѕРІ:\n"
            f"вЂў РџСЂРёРіР»Р°СЃРёС‚Рµ РґСЂСѓРіР° вЂ” +1 СЂР°СЃРєР»Р°Рґ рџЋЃ\n"
            f"вЂў РџРѕРґРїРёС€РёС‚РµСЃСЊ РЅР° РєР°РЅР°Р» вЂ” +3 СЂР°СЃРєР»Р°РґР° рџ“є\n"
            f"вЂў РљСѓРїРёС‚Рµ РїР°РєРµС‚ СЂР°СЃРєР»Р°РґРѕРІ СЃРѕ СЃРєРёРґРєРѕР№ рџ’і"
        )
        keyboard = [
            [InlineKeyboardButton("рџ’і РљСѓРїРёС‚СЊ СЂР°СЃРєР»Р°РґС‹", callback_data='buy_packs')],
            [InlineKeyboardButton("рџ’« РџСЂРёРіР»Р°СЃРёС‚СЊ РґСЂСѓРіР°", callback_data='referral')],
            [InlineKeyboardButton("рџ“є РџРѕРґРїРёСЃР°С‚СЊСЃСЏ (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'referral':
        ref_link = f"https://t.me/cardnotlie_bot?start={user_id}"
        referral_count = get_referral_count(user_id)
        message = (
            f"рџЋЃ Р Р•Р¤Р•Р РђР›Р¬РќРђРЇ РџР РћР“Р РђРњРњРђ рџЋЃ\n\n"
            f"вњЁ Р’Р°С€Р° СЂРµС„РµСЂР°Р»СЊРЅР°СЏ СЃСЃС‹Р»РєР°:\n"
            f"{ref_link}\n\n"
            f"рџ“Љ РџСЂРёРіР»Р°С€РµРЅРѕ РґСЂСѓР·РµР№: {referral_count}\n"
            f"рџ’« Р—Р° РєР°Р¶РґРѕРіРѕ РґСЂСѓРіР° вЂ” +1 Р±РµСЃРїР»Р°С‚РЅС‹Р№ СЂР°СЃРєР»Р°Рґ!\n\n"
            f"рџ“¤ РџСЂРѕСЃС‚Рѕ РѕС‚РїСЂР°РІСЊС‚Рµ СЃСЃС‹Р»РєСѓ РґСЂСѓР·СЊСЏРј РёР»Рё РІ СЃРѕС†СЃРµС‚Рё!"
        )
        keyboard = [[InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'buy_packs':
        message = (
            "рџ’і РЎРџРћРЎРћР‘Р« РћРџР›РђРўР« рџ’і\n"
            "\nР’С‹Р±РµСЂРёС‚Рµ СѓРґРѕР±РЅС‹Р№ СЃРїРѕСЃРѕР±:\n"
            "\nрџЏ¦ Р‘Р°РЅРєРѕРІСЃРєР°СЏ РєР°СЂС‚Р° вЂ” С‚СЂРµР±СѓРµС‚СЃСЏ СЂСѓС‡РЅР°СЏ РїСЂРѕРІРµСЂРєР° СЃРєСЂРёРЅС€РѕС‚Р° вЏі\n"
            "рџ’Ћ РљСЂРёРїС‚РѕРІР°Р»СЋС‚Р° вЂ” РІ СЂР°Р·СЂР°Р±РѕС‚РєРµ рџ”њ"
        )
        keyboard = [
            [InlineKeyboardButton("рџЏ¦ Р‘Р°РЅРєРѕРІСЃРєР°СЏ РєР°СЂС‚Р°", callback_data='card_packs')],
            [InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'card_packs':
        message = (
            "рџ’і РџРђРљР•РўР« Р РђРЎРљР›РђР”РћР’ рџ’і\n"
            "\nвњЁ Р’С‹Р±РµСЂРёС‚Рµ РїР°РєРµС‚ СЃРѕ СЃРєРёРґРєРѕР№:\n"
            "\nрџЋґ 1 СЂР°СЃРєР»Р°Рґ вЂ” 100 в‚Ѕ\n"
            "   РРґРµР°Р»СЊРЅРѕ РґР»СЏ СЂР°Р·РѕРІРѕРіРѕ РіР°РґР°РЅРёСЏ.\n"
            "\nрџЋґ 3 СЂР°СЃРєР»Р°РґР° вЂ” 285 в‚Ѕ (-5%)\n"
            "   Р­РєРѕРЅРѕРјРёСЏ 15 в‚Ѕ.\n"
            "\nрџЋґ 7 СЂР°СЃРєР»Р°РґРѕРІ вЂ” 630 в‚Ѕ (-10%)\n"
            "   Р­РєРѕРЅРѕРјРёСЏ 70 в‚Ѕ.\n"
            "\nрџЋґ 13 СЂР°СЃРєР»Р°РґРѕРІ вЂ” 1 105 в‚Ѕ (-15%)\n"
            "   Р­РєРѕРЅРѕРјРёСЏ 195 в‚Ѕ."
        )
        keyboard = [
            [InlineKeyboardButton("1 СЂР°СЃРєР»Р°Рґ вЂ” 100в‚Ѕ", callback_data='buy_1')],
            [InlineKeyboardButton("3 СЂР°СЃРєР»Р°РґР° вЂ” 285в‚Ѕ (-5%)", callback_data='buy_3')],
            [InlineKeyboardButton("7 СЂР°СЃРєР»Р°РґРѕРІ вЂ” 630в‚Ѕ (-10%)", callback_data='buy_7')],
            [InlineKeyboardButton("13 СЂР°СЃРєР»Р°РґРѕРІ вЂ” 1 105в‚Ѕ (-15%)", callback_data='buy_13')],
            [InlineKeyboardButton("в¬…пёЏ РќР°Р·Р°Рґ", callback_data='buy_packs')]
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
            f"рџ’і РћРџР›РђРўРђ РџРђРљР•РўРђ: {pack_size} СЂР°СЃРєР»Р°РґРѕРІ рџ’і\n"
            f"\nрџ’° РЎС‚РѕРёРјРѕСЃС‚СЊ: {price} в‚Ѕ (СЃРєРёРґРєР° {discount})\n"
            f"\nрџЏ¦ Р РµРєРІРёР·РёС‚С‹ РґР»СЏ РѕРїР»Р°С‚С‹:\n"
            f"в–«пёЏ Р‘Р°РЅРє: Р Р°Р№С„С„Р°Р№Р·РµРЅР±Р°РЅРє.\n"
            f"в–«пёЏ РќРѕРјРµСЂ РєР°СЂС‚С‹: \n"
            f"в–«пёЏ РџРѕР»СѓС‡Р°С‚РµР»СЊ: РЎРµСЂРіРµР№ Р›.\n"
            f"в–«пёЏ РЎСѓРјРјР°: {price} в‚Ѕ.\n"
            f"\nвњ… РџРћРЎР›Р• РћРџР›РђРўР«:\n"
            f"1. РЎРґРµР»Р°Р№С‚Рµ СЃРєСЂРёРЅС€РѕС‚ РїРµСЂРµРІРѕРґР°.\n"
            f"2. РќР°РїРёС€РёС‚Рµ РІ РїРѕРґРґРµСЂР¶РєСѓ @jobphone_admin СЃ РїРѕРјРµС‚РєРѕР№ В«РћРџР›РђРўРђВ».\n"
            f"3. РњС‹ РЅР°С‡РёСЃР»РёРј {pack_size} СЂР°СЃРєР»Р°РґРѕРІ РЅР° РІР°С€ Р±Р°Р»Р°РЅСЃ РІ С‚РµС‡РµРЅРёРµ 10 РјРёРЅСѓС‚! вњЁ\n"
            f"\nв„№пёЏ РџРѕРґСЂРѕР±РЅРµРµ РѕР± СѓСЃР»РѕРІРёСЏС… РѕРїР»Р°С‚С‹: /terms"
        )
        keyboard = [
            [InlineKeyboardButton("в¬…пёЏ РќР°Р·Р°Рґ Рє РїР°РєРµС‚Р°Рј", callback_data='card_packs')],
            [InlineKeyboardButton("рџ“„ РЈСЃР»РѕРІРёСЏ РѕРїР»Р°С‚С‹", callback_data='terms')],
            [InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'terms' or query.data == 'terms_button':
        message = (
            "рџ“„ РЈРЎР›РћР’РРЇ РћРџР›РђРўР« Р РЎРћР“Р›РђРЎРР• рџ“„\n"
            "\nрџ’« Р’РђР–РќРћ: Р»СЋР±Р°СЏ РѕРїР»Р°С‚Р° РІ СЌС‚РѕРј Р±РѕС‚Рµ СЏРІР»СЏРµС‚СЃСЏ Р”РћР‘Р РћР’РћР›Р¬РќР«Рњ Р”РћРќРђРўРћРњ.\n"
            "Р Р°СЃРєР»Р°РґС‹ РўР°СЂРѕ РїСЂРµРґРѕСЃС‚Р°РІР»СЏСЋС‚СЃСЏ РІ СЂР°Р·РІР»РµРєР°С‚РµР»СЊРЅС‹С… С†РµР»СЏС….\n"
            "РРЅС‚РµСЂРїСЂРµС‚Р°С†РёРё РєР°СЂС‚ РЅРµ СЏРІР»СЏСЋС‚СЃСЏ РїСЂРµРґСЃРєР°Р·Р°РЅРёРµРј Р±СѓРґСѓС‰РµРіРѕ Рё РЅРµ Р·Р°РјРµРЅСЏСЋС‚ РєРѕРЅСЃСѓР»СЊС‚Р°С†РёСЋ СЃРїРµС†РёР°Р»РёСЃС‚Р°.\n"
            "\nвњ… РќР°Р¶РёРјР°СЏ В«РћРїР»Р°С‚РёС‚СЊВ», РІС‹ СЃРѕРіР»Р°С€Р°РµС‚РµСЃСЊ СЃ С‚РµРј, С‡С‚Рѕ:\n"
            "вЂў РћРїР»Р°С‚Р° РґРѕР±СЂРѕРІРѕР»СЊРЅР°СЏ Рё РЅРµРѕР±СЏР·Р°С‚РµР»СЊРЅР°СЏ.\n"
            "вЂў Р Р°СЃРєР»Р°РґС‹ РЅРѕСЃСЏС‚ СЂР°Р·РІР»РµРєР°С‚РµР»СЊРЅС‹Р№ С…Р°СЂР°РєС‚РµСЂ.\n"
            "вЂў Р’С‹ СЃРѕРІРµСЂС€Р°РµС‚Рµ РїР»Р°С‚С‘Р¶ РїРѕ СЃРѕР±СЃС‚РІРµРЅРЅРѕР№ РІРѕР»Рµ Р±РµР· РїСЂРёРЅСѓР¶РґРµРЅРёСЏ.\n"
            "вЂў Р’РѕР·РІСЂР°С‚ СЃСЂРµРґСЃС‚РІ РЅРµ РїСЂРµРґСѓСЃРјРѕС‚СЂРµРЅ (РґРѕР±СЂРѕРІРѕР»СЊРЅС‹Р№ РґРѕРЅР°С‚).\n"
            "\nвњЁ РЎРїР°СЃРёР±Рѕ Р·Р° РїРѕРґРґРµСЂР¶РєСѓ РїСЂРѕРµРєС‚Р°! рџ’«"
        )
        keyboard = [[InlineKeyboardButton("в¬…пёЏ РќР°Р·Р°Рґ Рє РѕРїР»Р°С‚Рµ", callback_data='buy_packs')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'subscribe':
        subscribed = check_subscribed(user_id)
        if subscribed:
            message = "вњ… Р’С‹ СѓР¶Рµ РїРѕРґРїРёСЃР°РЅС‹ РЅР° РЅР°С€ РєР°РЅР°Р»!\nрџ’« Р‘РѕРЅСѓСЃ +3 СЂР°СЃРєР»Р°РґР° СѓР¶Рµ РЅР°С‡РёСЃР»РµРЅ."
        else:
            message = (
                "рџ“є РџРћР”РџРРЎРљРђ РќРђ РљРђРќРђР› рџ“є\n"
                "\nРџРѕРґРїРёС€РёС‚РµСЃСЊ РЅР° РЅР°С€ СЌР·РѕС‚РµСЂРёС‡РµСЃРєРёР№ РєР°РЅР°Р» Рё РїРѕР»СѓС‡РёС‚Рµ +3 Р±РµСЃРїР»Р°С‚РЅС‹С… СЂР°СЃРєР»Р°РґР°!\n"
                "\nвњЁ РљР°РЅР°Р»: https://t.me/+5q7VJBPU4_QyMDky\n"
                "\nРџРѕСЃР»Рµ РїРѕРґРїРёСЃРєРё РЅР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ РЅРёР¶Рµ:"
            )
        keyboard = [
            [InlineKeyboardButton("рџ“є РџРµСЂРµР№С‚Рё РІ РєР°РЅР°Р»", url="https://t.me/+5q7VJBPU4_QyMDky")],
            [InlineKeyboardButton("вњ… РЇ РїРѕРґРїРёСЃР°Р»СЃСЏ (+3 СЂР°СЃРєР»Р°РґР°)", callback_data='confirm_subscribe')],
            [InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'confirm_subscribe':
        subscribed = check_subscribed(user_id)
        if subscribed:
            message = "вњ… Р’С‹ СѓР¶Рµ РїРѕР»СѓС‡РёР»Рё Р±РѕРЅСѓСЃ Р·Р° РїРѕРґРїРёСЃРєСѓ!"
        else:
            mark_subscribed(user_id)
            message = "рџЋ‰ РЈСЂР°! Р’С‹ РїРѕРґРїРёСЃР°Р»РёСЃСЊ РЅР° РєР°РЅР°Р»!\nвњЁ Р‘РѕРЅСѓСЃ +3 Р±РµСЃРїР»Р°С‚РЅС‹С… СЂР°СЃРєР»Р°РґР° РЅР°С‡РёСЃР»РµРЅ РЅР° РІР°С€ СЃС‡С‘С‚!"
        keyboard = [[InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'help':
        message = (
            "вќ“ РџРћРњРћР©Р¬ вќ“\n"
            "\nвњЁ РљРђРљ РџРћР›Р¬Р—РћР’РђРўР¬РЎРЇ Р‘РћРўРћРњ:\n"
            "вЂў рџЊ… РљР°СЂС‚Р° РґРЅСЏ вЂ” Р±РµСЃРїР»Р°С‚РЅРѕРµ РіР°РґР°РЅРёРµ РЅР° СЃРµРіРѕРґРЅСЏ (1 СЂР°Р· РІ РґРµРЅСЊ)\n"
            "вЂў рџЋґ РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ вЂ” РїРѕРґСЂРѕР±РЅС‹Р№ СЂР°СЃРєР»Р°Рґ РёР· 3+ РєР°СЂС‚ (СЃРїРёСЃС‹РІР°РµС‚СЃСЏ СЃ Р±Р°Р»Р°РЅСЃР°)\n"
            "вЂў рџ’ѕ РЎРѕС…СЂР°РЅРёС‚СЊ СЂР°СЃРєР»Р°Рґ вЂ” СЃРѕС…СЂР°РЅРёС‚Рµ СЂРµР·СѓР»СЊС‚Р°С‚ РІ РѕРґРЅСѓ РёР· 3 СЏС‡РµРµРє\n"
            "\nрџ—„пёЏ РЎРћРҐР РђРќР•РќРР• Р РђРЎРљР›РђР”РћР’:\n"
            "вЂў РЈ РІР°СЃ РµСЃС‚СЊ 3 СЏС‡РµР№РєРё РґР»СЏ СЃРѕС…СЂР°РЅРµРЅРёСЏ СЂР°СЃРєР»Р°РґРѕРІ.\n"
            "вЂў Р Р°СЃРєР»Р°РґС‹ РќР• СЃРѕС…СЂР°РЅСЏСЋС‚СЃСЏ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё вЂ” С‚РѕР»СЊРєРѕ РїРѕ РІР°С€РµРјСѓ РІС‹Р±РѕСЂСѓ.\n"
            "вЂў Р•СЃР»Рё РІСЃРµ СЏС‡РµР№РєРё Р·Р°РЅСЏС‚С‹ вЂ” СЃРЅР°С‡Р°Р»Р° СѓРґР°Р»РёС‚Рµ СЃС‚Р°СЂС‹Р№ СЂР°СЃРєР»Р°Рґ.\n"
            "\nвљ–пёЏ Р‘РђР›РђРќРЎ:\n"
            "вЂў РџСЂРё СЂРµРіРёСЃС‚СЂР°С†РёРё: 1 Р±РµСЃРїР»Р°С‚РЅС‹Р№ СЂР°СЃРєР»Р°Рґ.\n"
            "вЂў рџЊ… РљР°СЂС‚Р° РґРЅСЏ вЂ” РІСЃРµРіРґР° Р±РµСЃРїР»Р°С‚РЅРѕ, 1 СЂР°Р· РІ РґРµРЅСЊ.\n"
            "вЂў Р—Р° РґСЂСѓРіР°: +1 СЂР°СЃРєР»Р°Рґ.\n"
            "вЂў Р—Р° РїРѕРґРїРёСЃРєСѓ: +3 СЂР°СЃРєР»Р°РґР°.\n"
            "вЂў РџРѕРєСѓРїРєР° РїР°РєРµС‚РѕРІ СЃРѕ СЃРєРёРґРєРѕР№ РґРѕ 15%.\n"
            "\nрџ’і РћРџР›РђРўРђ:\n"
            "вЂў Р‘Р°РЅРєРѕРІСЃРєР°СЏ РєР°СЂС‚Р° вЂ” СЂСѓС‡РЅР°СЏ РїСЂРѕРІРµСЂРєР° СЃРєСЂРёРЅС€РѕС‚Р° вЏі\n"
            "вЂў РљСЂРёРїС‚РѕРІР°Р»СЋС‚Р° вЂ” РІ СЂР°Р·СЂР°Р±РѕС‚РєРµ рџ”њ\n"
            "вЂў РџРѕРґСЂРѕР±РЅРµРµ РѕР± СѓСЃР»РѕРІРёСЏС…: /terms"
        )
        keyboard = [[InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=message, reply_markup=reply_markup)
    
    elif query.data == 'back_to_menu':
        user_data = get_user_data(user_id)
        if not user_data or not user_data.get('name'):
            await query.message.reply_text("РќР°РїРёС€РёС‚Рµ СЃРІРѕС‘ РёРјСЏ:")
            return
        
        balance = get_balance(user_id)
        message = f"рџ”® Р”РћР‘Р Рћ РџРћР–РђР›РћР’РђРўР¬ Р’ РњРР  РўРђР Рћ! рџ”®\nвњЁ {user_data['name']}, РІР°С€ Р±Р°Р»Р°РЅСЃ: {balance} СЂР°СЃРєР»Р°РґРѕРІ"
        keyboard = [
            [InlineKeyboardButton("рџЊ… РљР°СЂС‚Р° РґРЅСЏ (Р±РµСЃРїР»Р°С‚РЅРѕ)", callback_data='daily_card')],
            [InlineKeyboardButton("рџЋґ РЎРґРµР»Р°С‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')],
            [InlineKeyboardButton(f"вљ–пёЏ Р‘Р°Р»Р°РЅСЃ: {balance}", callback_data='balance')],
            [InlineKeyboardButton("рџ“є РџРѕРґРїРёСЃРєР° (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("рџ—„пёЏ РњРѕРё СЂР°СЃРєР»Р°РґС‹", callback_data='saved_readings')],
            [InlineKeyboardButton("вќ“ РџРѕРјРѕС‰СЊ", callback_data='help')]
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
            [InlineKeyboardButton("рџ’і РљСѓРїРёС‚СЊ СЂР°СЃРєР»Р°РґС‹", callback_data='buy_packs')],
            [InlineKeyboardButton("рџ“є РџРѕРґРїРёСЃР°С‚СЊСЃСЏ (+3)", callback_data='subscribe')],
            [InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="рџ’« РЈ РІР°СЃ Р·Р°РєРѕРЅС‡РёР»РёСЃСЊ СЂР°СЃРєР»Р°РґС‹.\nрџ’° РџРѕРїРѕР»РЅРёС‚Рµ Р±Р°Р»Р°РЅСЃ РёР»Рё РїРѕР»СѓС‡РёС‚Рµ Р±РѕРЅСѓСЃС‹!",
            reply_markup=reply_markup
        )
        return
    
    spreads = get_spread_options()
    # РЈР±РёСЂР°РµРј РєР°СЂС‚Сѓ РґРЅСЏ РёР· СЃРїРёСЃРєР° РїР»Р°С‚РЅС‹С… СЂР°СЃРєР»Р°РґРѕРІ
    spreads.pop('daily', None)
    
    message = "рџЋґ Р’Р«Р‘Р•Р РРўР• РўРРџ Р РђРЎРљР›РђР”Рђ рџЋґ\n\n"
    keyboard = []
    
    for spread_id, spread_info in spreads.items():
        keyboard.append([InlineKeyboardButton(spread_info['name'], callback_data=f'spread_{spread_id}')])
    
    keyboard.append([InlineKeyboardButton("в¬…пёЏ РќР°Р·Р°Рґ", callback_data='back_to_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=message, reply_markup=reply_markup)


# ... (РЅР°С‡Р°Р»Рѕ С„Р°Р№Р»Р° Р±РµР· РёР·РјРµРЅРµРЅРёР№) ...

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
        await query.edit_message_text(text="вќЊ РЈ РІР°СЃ РЅРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ СЂР°СЃРєР»Р°РґРѕРІ. РџРѕРїРѕР»РЅРёС‚Рµ Р±Р°Р»Р°РЅСЃ!")
        return
    
    # вњ… РРЎРџР РђР’Р›Р•РќРћ: СЃРїРёСЃС‹РІР°РµРј Р’РЎР•Р“Р”Рђ 1 СЂР°СЃРєР»Р°Рґ (РЅРµР·Р°РІРёСЃРёРјРѕ РѕС‚ РєРѕР»РёС‡РµСЃС‚РІР° РєР°СЂС‚)
    if not decrease_balance(user_id, 1):
        await query.edit_message_text(text="вќЊ РћС€РёР±РєР° РїСЂРё СЃРїРёСЃР°РЅРёРё СЂР°СЃРєР»Р°РґР°. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРѕР·Р¶Рµ.")
        return
    
    new_balance = get_balance(user_id)
    spreads = get_spread_options()
    
    if spread_id not in spreads:
        await query.edit_message_text(text=f"вќЊ РќРµРІРµСЂРЅС‹Р№ С‚РёРї СЂР°СЃРєР»Р°РґР°: '{spread_id}'. Р”РѕСЃС‚СѓРїРЅС‹Рµ: {', '.join(spreads.keys())}")
        return
    
    spread_info = spreads[spread_id]
    try:
        cards = get_random_cards(spread_info['cards_count'])
        reading = format_reading(cards, user_data['name'], spread_info['positions'])
    except Exception as e:
        # Р’РѕР·РІСЂР°С‚ Р±Р°Р»Р°РЅСЃР° РїСЂРё РѕС€РёР±РєРµ РіРµРЅРµСЂР°С†РёРё
        increase_balance(user_id, 1)
        await query.edit_message_text(text=f"вќЊ РћС€РёР±РєР° РіРµРЅРµСЂР°С†РёРё СЂР°СЃРєР»Р°РґР°: {str(e)[:100]}\nР‘Р°Р»Р°РЅСЃ РІРѕР·РІСЂР°С‰С‘РЅ.")
        return
    
    if 'pending_readings' not in context.user_data:
        context.user_data['pending_readings'] = {}
    context.user_data['pending_readings'][user_id] = (cards, reading)
    
    # РћС‚РїСЂР°РІР»СЏРµРј СЂР°СЃРєР»Р°Рґ РєР°Рє РћРўР”Р•Р›Р¬РќРћР• СЃРѕРѕР±С‰РµРЅРёРµ (РЅРµ СЂРµРґР°РєС‚РёСЂСѓРµРј РєРЅРѕРїРєРё)
    await context.bot.send_message(chat_id=query.message.chat_id, text=reading)
    
    keyboard = [
        [InlineKeyboardButton("рџ’ѕ РЎРѕС…СЂР°РЅРёС‚СЊ СЂР°СЃРєР»Р°Рґ", callback_data='save_last_reading')],
        [InlineKeyboardButton("рџ”„ Р•С‰С‘ РѕРґРёРЅ СЂР°СЃРєР»Р°Рґ", callback_data='do_tarot')],
        [InlineKeyboardButton(f"вљ–пёЏ Р‘Р°Р»Р°РЅСЃ: {new_balance}", callback_data='balance')],
        [InlineKeyboardButton("в¬…пёЏ РњРµРЅСЋ", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="рџ’« Р Р°СЃРєР»Р°Рґ РіРѕС‚РѕРІ! рџ’ѕ РЎРѕС…СЂР°РЅРёС‚Рµ РµРіРѕ, С‡С‚РѕР±С‹ РЅРµ РїРѕС‚РµСЂСЏС‚СЊ.",
        reply_markup=reply_markup
    )
