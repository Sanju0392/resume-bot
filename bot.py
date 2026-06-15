"""
Resume Automation Bot
Telegram → Claude AI → Google Drive → Naukri
"""

import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from workflow import run_pipeline

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

from config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Resume bot ready.\n\n"
        "Just send me a message about what you did today — "
        "I'll decide if it's resume-worthy, update your Drive resume, and sync Naukri.\n\n"
        "Commands:\n"
        "/status — check last update\n"
        "/resume — get your current resume\n"
        "/help — show this message"
    )


async def status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from state import load_state
    s = load_state()
    if not s.get("last_update"):
        await update.message.reply_text("No updates yet.")
        return
    await update.message.reply_text(
        f"📋 Last resume update:\n"
        f"Date: {s['last_update']}\n"
        f"Section: {s.get('last_section', '—')}\n"
        f"Achievement: {s.get('last_achievement', '—')[:120]}..."
    )


async def get_resume(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from drive import download_resume
    await update.message.reply_text("⏳ Fetching your resume from Drive...")
    try:
        text = download_resume("resume_base")
        await update.message.reply_text(f"📄 Current resume:\n\n{text[:3000]}")
    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch resume: {e}")


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("❌ Unauthorized.")
        return

    msg = update.message.text.strip()
    if not msg:
        return

    log.info(f"Message from {user_id}: {msg[:80]}")
    await update.message.reply_text("🔍 Analysing your update...")

    try:
        result = await run_pipeline(msg)

        if result["verdict"] == "NOT_WORTHY":
            await update.message.reply_text(
                f"📭 Not resume-worthy.\n\n"
                f"Reason: {result['reason']}\n\n"
                f"Send a more specific achievement with measurable impact."
            )
            return

        await update.message.reply_text(
            f"✅ Resume updated!\n\n"
            f"📌 Section: {result['section']}\n"
            f"📝 Added: {result['achievement'][:200]}\n\n"
            f"📊 ATS score: {result['ats_score']}/100\n"
            f"📄 Pages: {result['pages']}\n\n"
            f"☁️ Saved to Drive:\n"
            f"  • resume_base.pdf (base)\n"
            f"  • resume_{result['date']}.pdf (latest)\n\n"
            f"🔄 Naukri sync: {result['naukri_status']}"
        )

    except Exception as e:
        log.error(f"Pipeline error: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Something went wrong: {str(e)}\n"
            f"Check logs for details."
        )


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("resume", get_resume))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if render_url:
        port = int(os.getenv("PORT", 10000))
        log.info(f"Starting webhook on port {port} at {render_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"{render_url}/{TELEGRAM_BOT_TOKEN}",
            drop_pending_updates=True,
        )
    else:
        log.info("Bot started — polling for messages...")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
