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
import os, threading, http.server, socketserver

# ------------------------------------------------------------------ KEEP-ALIVE
import os, threading, http.server, socketserver

def _ping():
    port = int(os.environ.get("PORT", 10000))
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    with socketserver.TCPServer(("0.0.0.0", port), Handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=_ping, daemon=True).start()


TOKEN = os.environ["TOKEN"]        # <-- token ottenuto da @BotFather


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
            "Qui doniamo cibo in scadenza per evitare che finisca nella spazzatura.\n\n"
            "👣 *Come funziona*\n"
            "• Per offrire → scrivi `/regala (3 yogurt scadenza 25/05)`\n"
            "• Vuoi qualcosa? premi *Prenota* (vale solo il primo!)\n"
            "• Il bot mette in contatto privato chi offre e chi prenota.\n\n"
            "📜 *Regole*\n\n"
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
            "Here we gift soon-to-expire food so it doesn’t end up in the bin.\n\n"
            "👣 *How it works*\n"
            "• To offer → write `/regala (3 yogurts exp 25/05)`\n"
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
T["it"]["cancel_button"] = "❌ Annulla"
T["it"]["canceled_msg"]  = "🔄 Prenotazione annullata da {u}. Annuncio di nuovo disponibile!"
T["en"]["cancel_button"] = "❌ Cancel"
T["en"]["canceled_msg"]  = "🔄 Booking canceled by {u}. Offer is available again!"
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
        await update.message.reply_text(tr("need_desc", context.user_data), parse_mode="Markdown")
        return

    descr   = " ".join(context.args)
    don     = update.effective_user
    don_tag = f"@{don.username}" if don.username else don.first_name

    # salva draft
    context.chat_data["draft"] = {
        "descr": descr,
        "lang":  lang_of(context.user_data),
        "don_id": don.id,
        "don_tag": don_tag,
        "state": "WAIT_ACTION",
        "prompt_id": prompt_msg.message_id
    }

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📷 Aggiungi foto", callback_data="draft|photo"),
         InlineKeyboardButton("🚀 Pubblica subito", callback_data="draft|publish")]
    ])
    prompt_msg = await update.message.reply_text(
      "Vuoi allegare una foto?", reply_markup=kb
    )

async def draft_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = update.callback_query.data.split("|")[1]
    draft  = context.chat_data.get("draft")

    if not draft or draft["state"] != "WAIT_ACTION":
        await update.callback_query.answer("Nessun annuncio in preparazione.")
        return

    if action == "photo":
        draft["state"] = "WAIT_PHOTO"
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Ok! Inviami la foto come immagine singola.")
    elif action == "publish":
        await publish_announcement(update.effective_chat.id, context, draft, photo=None)
        # elimina il messaggio prompt
        await context.bot.delete_message(update.effective_chat.id, draft["prompt_id"])
        context.chat_data.pop("draft")
        await update.callback_query.answer("Annuncio pubblicato!")


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.chat_data.get("draft")
    if not draft or draft["state"] != "WAIT_PHOTO":
        return

    photo_id = update.message.photo[-1].file_id
    await publish_announcement(update.effective_chat.id, context, draft, photo=photo_id)

    # elimina il prompt "Vuoi allegare..." (se ancora esiste)
    await context.bot.delete_message(update.effective_chat.id, draft["prompt_id"])
    # elimina la foto che l'utente ha appena inviato
    await context.bot.delete_message(update.effective_chat.id, update.message.message_id)

    context.chat_data.pop("draft")
    await update.message.reply_text("Annuncio con foto pubblicato ✅")


async def publish_announcement(chat_id, context, draft, photo=None):
    text = T[draft["lang"]]["offer_prefix"].format(
        don_tag=draft["don_tag"], descrizione=draft["descr"]
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(T[draft["lang"]]["button_book"], callback_data="book")]
    ])

    if photo:
        msg = await context.bot.send_photo(chat_id, photo=photo, caption=text, reply_markup=kb, parse_mode="Markdown")
    else:
        msg = await context.bot.send_message(chat_id, text=text, reply_markup=kb, parse_mode="Markdown")

    # memorizza meta-info per prenotazioni
    context.chat_data[msg.message_id] = {
        "don_id": draft["don_id"],
        "don_tag": draft["don_tag"],
        "booked": False,
        "lang": draft["lang"]
    }


# prenotazione
async def book_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    aid  = q.message.message_id
    data = context.chat_data.get(aid)

    # controlli
    if not data:
        await q.answer("Error.")
        return
    if data["booked"]:
        await q.answer(tr("already_booked", context.user_data), show_alert=True)
        return

    user    = q.from_user
    u_tag   = f"@{user.username}" if user.username else user.first_name
    data["booked"] = True

    # --- bottone Annulla solo per il prenotante ---
    cancel_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            T[data["lang"]]["cancel_button"],
            callback_data=f"cancel|{aid}|{user.id}"    # cancel|idAnnuncio|idPrenotante
        )
    ]])

    # salva il testo originale se non già presente
    data["original_text"] = data.get("original_text", q.message.text)

    # aggiorna annuncio con ✅ e bottone Annulla
    await q.edit_message_text(
        f"{q.message.text}\n\n{T[data['lang']]['booked_mark'].format(user_tag=u_tag)}",
        reply_markup=cancel_kb,
        parse_mode="Markdown"
    )
    await q.answer(tr("you_booked", context.user_data))

    # avvisa gruppo
    await context.bot.send_message(
        q.message.chat_id,
        T[data['lang']]["group_notify"].format(user_tag=u_tag, don_tag=data["don_tag"])
    )

    # DM al donatore
    try:
        await context.bot.send_message(
            data["don_id"],
            T[data['lang']]["don_dm"].format(user_tag=u_tag)
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

async def cb_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    _, annuncio_id, prenotante_id = q.data.split("|")
    annuncio_id = int(annuncio_id)

    # controllo che clicchi proprio chi aveva prenotato
    if str(q.from_user.id) != prenotante_id:
        await q.answer("Non puoi annullare questa prenotazione.", show_alert=True)
        return

    data = context.chat_data.get(annuncio_id)
    if not data or not data["booked"]:
        await q.answer("Già annullata o non valida.", show_alert=True)
        return

    data["booked"] = False  # libera l'annuncio

    # ricrea bottone Prenota
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(T[data['lang']]["button_book"], callback_data="book")
    ]])

    await context.bot.edit_message_text(
        chat_id=q.message.chat_id,
        message_id=annuncio_id,
        text=data["original_text"],          # salvala quando crei l'annuncio
        reply_markup=kb,
        parse_mode="Markdown"
    )

    u_tag = f"@{q.from_user.username}" if q.from_user.username else q.from_user.first_name
    await context.bot.send_message(
        q.message.chat_id,
        T[data['lang']]["canceled_msg"].format(u=u_tag)
    )
    await q.answer("Prenotazione annullata!")

# ---------------------------------------------------------------------------#
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang\\|"))
    app.add_handler(CommandHandler("regole", rules_cmd))
    app.add_handler(CommandHandler("regala", regala_cmd))
    app.add_handler(CallbackQueryHandler(book_callback, pattern="^book$"))
    app.add_handler(CallbackQueryHandler(cb_cancel,  pattern="^cancel\\|"))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(CallbackQueryHandler(draft_callback, pattern="^draft\\|"))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    logging.basicConfig(level=logging.INFO)
    logger.info("Bot avviato.")
    app.run_polling()

if __name__ == "__main__":
    main()
