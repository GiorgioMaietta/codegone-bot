"""
Bot Telegram – Residenza Codegone  ♻️🥗
Riduzione sprechi alimentari (annunci /regala  + prenotazione) con supporto IT/EN.
python-telegram-bot 20.x
"""

import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

TOKEN = "7713879857:AAEZ222wslWVIdVG1JBQ5ot5kIesacVYziw"        # <-- token ottenuto da @BotFather

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------#
# 1) TESTI – dizionario di traduzioni
T = {
    "it": {
        "rules": (
            "🍏 *Benvenuto/a in Residenza Codegone – Zero Sprechi!* ♻️\n\n"
            "Qui scambiamo cibo in scadenza per evitare che finisca nella spazzatura.\n\n"
            "👣 *Come funziona*\n"
            "• Per offrire → `/regala 3 yogurt scadenza 25/05`\n"
            "• Vuoi qualcosa? premi *Prenota* (vale solo il primo!)\n"
            "• Il bot mette in contatto privato chi offre e chi prenota.\n\n"
            "📜 *Regole*\n"
            "1️⃣ Solo cibo commestibile e ben confezionato.\n"
            "2️⃣ Niente spam / volgarità / off-topic.\n"
            "3️⃣ Rispetta gli accordi: se prenoti, ritira.\n"
            "4️⃣ Dubbi? contatta i moderatori.\n\n"
            "Grazie per l’aiuto a ridurre lo spreco! 🌱"
        ),
        "need_desc": "❗️Sintassi: `/regala <descrizione>`\nEsempio: `/regala 2 banane mature`",
        "offer_prefix": "🎁 {don_tag} offre: *{descrizione}*",
        "button_book": "Prenota 🛎️",
        "already_booked": "Già prenotato da un altro utente.",
        "booked_mark": "✅ Prenotato da {user_tag}",
        "group_notify": "{user_tag} ha prenotato l’annuncio di {don_tag}. Contattatevi in privato!",
        "don_dm": "{user_tag} ha prenotato ciò che hai offerto nel gruppo Residenza Codegone.",
        "you_booked": "👍 Prenotazione registrata!",
        "start": (
            "Ciao! Questo bot funziona nel gruppo *Residenza Codegone*.\n"
            "Usa /regala per offrire cibo.\n\n"
            "Se vuoi cambiare lingua → /lang"
        ),
        "lang_choose": "Seleziona la lingua / Choose language:",
        "lang_set_it": "Lingua impostata su 🇮🇹 Italiano.",
        "lang_set_en": "Language set to 🇬🇧 English."
    },
    "en": {
        "rules": (
            "🍏 *Welcome to Codegone Residence – Zero Waste!* ♻️\n\n"
            "Here we swap soon-to-expire food so it doesn’t end up in the bin.\n\n"
            "👣 *How it works*\n"
            "• To offer → `/regala 3 yogurts exp 25/05`\n"
            "• Need something? hit *Book* (only the first counts!)\n"
            "• The bot puts giver & receiver in private contact.\n\n"
            "📜 *Rules*\n"
            "1️⃣ Only edible food, properly packed.\n"
            "2️⃣ No spam / insults / off-topic.\n"
            "3️⃣ Keep your word: if you book, collect it.\n"
            "4️⃣ Questions? ask the mods.\n\n"
            "Thanks for helping us cut food waste! 🌱"
        ),
        "need_desc": "❗️Syntax: `/regala <description>`\nExample: `/regala 2 ripe bananas`",
        "offer_prefix": "🎁 {don_tag} offers: *{descrizione}*",
        "button_book": "Book 🛎️",
        "already_booked": "Already booked by someone else.",
        "booked_mark": "✅ Booked by {user_tag}",
        "group_notify": "{user_tag} booked {don_tag}’s offer. DM each other!",
        "don_dm": "{user_tag} booked the food you offered in Codegone Residence group.",
        "you_booked": "👍 Booking confirmed!",
        "start": (
            "Hi! This bot works inside *Codegone Residence* group.\n"
            "Use /regala to offer food.\n\n"
            "Change language → /lang"
        ),
        "lang_choose": "Seleziona la lingua / Choose language:",
        "lang_set_it": "Lingua impostata su 🇮🇹 Italiano.",
        "lang_set_en": "Language set to 🇬🇧 English."
    },
}

# ---------------------------------------------------------------------------#
def lang_of(user_data):
    """ritorna 'it' o 'en' (default it)"""
    return user_data.get("lang", "it")

def tr(key, user_data, **fmt):
    return T[lang_of(user_data)][key].format(**fmt)

# memorizzo dati annuncio in chat_data[message_id] = {...}
# ---------------------------------------------------------------------------#
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        tr("start", context.user_data), parse_mode="Markdown"
    )

async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Italiano 🇮🇹", callback_data="lang|it"),
         InlineKeyboardButton("English 🇬🇧",  callback_data="lang|en")]
    ])
    await update.message.reply_text(tr("lang_choose", context.user_data), reply_markup=kb)

async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.callback_query.data.split("|")[1]
    context.user_data["lang"] = code
    await update.callback_query.answer()
    msg = "lang_set_it" if code == "it" else "lang_set_en"
    await update.callback_query.edit_message_text(
        T[code][msg], parse_mode="Markdown"
    )

# /regole
async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await context.bot.send_message(
        update.effective_chat.id, tr("rules", context.user_data), parse_mode="Markdown"
    )
    try:
        await context.bot.pin_chat_message(update.effective_chat.id, msg.message_id)
    except Exception:
        pass

# /regala
async def regala_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            tr("need_desc", context.user_data), parse_mode="Markdown"
        )
        return
    descr = " ".join(context.args)
    don = update.effective_user
    don_tag = f"@{don.username}" if don.username else don.first_name
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(tr("button_book", context.user_data), callback_data="book")]]
    )
    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=tr("offer_prefix", context.user_data, don_tag=don_tag, descrizione=descr),
        reply_markup=kb,
        parse_mode="Markdown",
    )
    context.chat_data[msg.message_id] = {
        "don_id": don.id,
        "don_tag": don_tag,
        "booked": False,
        "lang": lang_of(context.user_data)
    }

# prenotazione
async def book_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    aid = q.message.message_id
    data = context.chat_data.get(aid)
    if not data:
        await q.answer("Error.")
        return
    if data["booked"]:
        await q.answer(tr("already_booked", context.user_data), show_alert=True)
        return

    user = q.from_user
    user_tag = f"@{user.username}" if user.username else user.first_name
    data["booked"] = True

    # edit annuncio
    new_text = f"{q.message.text}\n\n{T[data['lang']]['booked_mark'].format(user_tag=user_tag)}"
    await q.edit_message_text(new_text, parse_mode="Markdown")

    await q.answer(tr("you_booked", context.user_data))

    # notifica gruppo
    await context.bot.send_message(
        chat_id=q.message.chat_id,
        text=T[data['lang']]["group_notify"].format(
            user_tag=user_tag, don_tag=data["don_tag"]
        )
    )

    # DM al donatore (nella sua lingua!)
    try:
        await context.bot.send_message(
            chat_id=data["don_id"],
            text=T[data['lang']]["don_dm"].format(user_tag=user_tag)
        )
    except Exception:
        pass

# benvenuto nuovi membri
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for m in update.message.new_chat_members:
        tag = f"@{m.username}" if m.username else m.first_name
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"👋 {tag}\n\n{T['it']['rules']}\n\n{T['en']['rules']}",
            parse_mode="Markdown"
        )

# ---------------------------------------------------------------------------#
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang\\|"))
    app.add_handler(CommandHandler("regole", rules_cmd))
    app.add_handler(CommandHandler("regala", regala_cmd))
    app.add_handler(CallbackQueryHandler(book_callback, pattern="^book$"))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))

    logger.info("Bot avviato.")
    app.run_polling()

if __name__ == "__main__":
    main()
