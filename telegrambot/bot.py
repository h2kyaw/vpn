import os
import sys
import time
import logging
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = os.getenv("TELEGRAM_ALLOWED_USERS", "")
ALLOWED_USER_IDS = [int(uid.strip()) for uid in ALLOWED_USERS.split(",") if uid.strip().isdigit()] if ALLOWED_USERS else []

SCRIPT_PATH = "/home/hhk/Projects/vpn/hotspot-manager.py"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def check_authorization(user_id):
    if not ALLOWED_USER_IDS:
        return True # Allow all if no list provided
    return user_id in ALLOWED_USER_IDS

def run_hotspot_command(args):
    """Run hotspot-manager.py with sudo"""
    try:
        cmd = ["sudo", "python3", SCRIPT_PATH] + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), -1

async def get_status_text():
    stdout, stderr, code = run_hotspot_command(["--status"])
    if code != 0 and not stdout:
        return f"Error getting status:\n{stderr}"
    return stdout

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_authorization(update.effective_user.id):
        await update.message.reply_text("Unauthorized access.")
        return
    await update.message.reply_text("Welcome! Use commands like: status, restart, fix, clients")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_authorization(update.effective_user.id):
        return
    
    status_text = await get_status_text()
    
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        # Edit existing message if triggered by callback
        try:
            await update.callback_query.edit_message_text(text=status_text, reply_markup=reply_markup)
            await update.callback_query.answer()
        except Exception as e:
            logger.warning(f"Could not edit message: {e}")
            await update.callback_query.message.reply_text(text=status_text, reply_markup=reply_markup)
    else:
        # Send new message if triggered by command
        await update.message.reply_text(text=status_text, reply_markup=reply_markup)

async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Refreshing...")
    await status_command(update, context) # Re-use status logic to edit message

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_authorization(update.effective_user.id): return
    msg = await update.message.reply_text("Restarting Hotspot...")
    stdout, stderr, code = run_hotspot_command(["--restart"])
    response = stdout if stdout else stderr
    await msg.edit_text(f"Restart Result:\n{response}")

async def restart_vpn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_authorization(update.effective_user.id): return
    msg = await update.message.reply_text("Restarting VPN...")
    stdout, stderr, code = run_hotspot_command(["--restart-vpn"])
    response = stdout if stdout else stderr
    await msg.edit_text(f"VPN Restart Result:\n{response}")

async def fix_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_authorization(update.effective_user.id): return
    msg = await update.message.reply_text("Fixing issues...")
    stdout, stderr, code = run_hotspot_command(["--fix"])
    response = stdout if stdout else stderr
    await msg.edit_text(f"Fix Result:\n{response}")

async def clients_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_authorization(update.effective_user.id): return
    stdout, stderr, code = run_hotspot_command(["--clients"])
    response = stdout if stdout else stderr
    await update.message.reply_text(f"Connected Clients:\n{response}")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle commands without slash (e.g., 'status' instead of '/status')"""
    if not check_authorization(update.effective_user.id): return
    
    text = update.message.text.strip().lower()
    if text == "status":
        await status_command(update, context)
    elif text == "restart":
        await restart_command(update, context)
    elif text == "restart_vpn":
        await restart_vpn_command(update, context)
    elif text == "fix":
        await fix_command(update, context)
    elif text == "clients":
        await clients_command(update, context)

def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("restart", restart_command))
    app.add_handler(CommandHandler("restart_vpn", restart_vpn_command))
    app.add_handler(CommandHandler("fix", fix_command))
    app.add_handler(CommandHandler("clients", clients_command))
    
    # Callback for Refresh button
    app.add_handler(CallbackQueryHandler(refresh_callback, pattern="^refresh_status$"))
    
    # Handle text messages as commands (No slash)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    logger.info("Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()