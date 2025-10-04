from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "8150050966:AAEbSjfmsol5m3BCl1_xoo3xAOPXciaBWGk"

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"GROUP_ID: {chat_id}")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("id", get_id))

app.run_polling()
