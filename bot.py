import asyncio
import logging
import sys
import requests
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters
# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = '8254126250:AAHeMHAs_zyW9D0ZrNM0LHE6AXvAW2czfXM'
OLLAMA_MODEL = 'gemma4:31b-cloud' 
OLLAMA_URL = 'http://127.0.0.1:11434/api/chat'
ADMIN_USERNAME = '@nodokc' 
# -----------------

SYSTEM_PROMPT = """A plane crashed into a snow forest... (вставь сюда весь полный промпт с русского языка) ..."""

users_db = {}

logging.basicConfig(level=logging.INFO)

def get_keyboard():
    keyboard = [
        [KeyboardButton("🎭 Режим Выживших: ВКЛ"), KeyboardButton("🤖 Обычный режим: ВКЛ")],
        [KeyboardButton("💎 Подписки"), KeyboardButton("🆓 Получить Test")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    if user_id not in users_db:
        status = 'admin' if f"@{username}" == ADMIN_USERNAME else 'user'
        users_db[user_id] = {
            'status': status, 'history': [], 'requests_ai': 5, 
            'requests_surv': 0, 'ban_until': None, 
            'subscription_until': None, 'username': f"@{username}" if username else "Unknown", 
            'mode': 'normal'
        }

    await update.message.reply_text(
        f"Привет! Твой статус: {users_db[user_id]['status'].upper()}\nКоманды: /list",
        reply_markup=get_keyboard()
    )

# --- АДМИНСКИЕ КОМАНДЫ ---
async def set_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users_db.get(user_id, {}).get('status') != 'admin': return
    if not context.args: return
    target_user = context.args[0].lower()
    for uid, data in users_db.items():
        if data['username'].lower() == target_user:
            data['status'] = 'admin'
            await update.message.reply_text(f"✅ {target_user} теперь АДМИН!")
            return
    await update.message.reply_text("Юзер не найден.")

async def set_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users_db.get(user_id, {}).get('status') != 'admin': return
    if not context.args: return
    target_user = context.args[0].lower()
    for uid, data in users_db.items():
        if data['username'].lower() == target_user:
            data['status'] = 'vip'
            data['requests_surv'] = 10
            await update.message.reply_text(f"✅ {target_user} теперь VIP!")
            return
    await update.message.reply_text("Юзер не найден.")

async def set_god(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users_db.get(user_id, {}).get('status') != 'admin': return
    if not context.args: return
    target_user = context.args[0].lower()
    for uid, data in users_db.items():
        if data['username'].lower() == target_user:
            data['status'] = 'god'
            data['requests_surv'] = 50
            await update.message.reply_text(f"✅ {target_user} теперь GOD!")
            return
    await update.message.reply_text("Юзер не найден.")

async def delete_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users_db.get(user_id, {}).get('status') != 'admin': return
    if not context.args: return
    target_user = context.args[0].lower()
    for uid, data in users_db.items():
        if data['username'].lower() == target_user:
            data['status'] = 'user'
            await update.message.reply_text(f"🗑 {target_user} лишен подписки и стал обычным юзером.")
            return
    await update.message.reply_text("Юзер не найден.")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users_db.get(user_id, {}).get('status') != 'admin': return
    if len(context.args) < 2: return
    time_str, target_user = context.args[0], context.args[1].lower()
    ban_time = None
    if time_str == '1h': ban_time = datetime.now() + timedelta(hours=1)
    elif time_str == '1d': ban_time = datetime.now() + timedelta(days=1)
    elif time_str == 'ip': ban_time = datetime.now() + timedelta(days=36500)
    else: return
    for uid, data in users_db.items():
        if data['username'].lower() == target_user:
            data['ban_until'] = ban_time
            await update.message.reply_text(f"🚫 {target_user} забанен до {ban_time}")
            return

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users_db.get(user_id, {}).get('status') != 'admin': return
    if not context.args: return
    target_user = context.args[0].lower()
    for uid, data in users_db.items():
        if data['username'].lower() == target_user:
            data['ban_until'] = None
            await update.message.reply_text(f"✅ {target_user} разбанен!")
            return

async def give_reqs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users_db.get(user_id, {}).get('status') != 'admin': return
    if not context.args: return
    target_user = context.args[0].lower()
    for uid, data in users_db.items():
        if data['username'].lower() == target_user:
            data['requests_ai'] += 50
            await update.message.reply_text(f"🎁 {target_user} получил +50 обычных запросов!")
            return

async def gives_reqs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if users_db.get(user_id, {}).get('status') != 'admin': return
    if not context.args: return
    target_user = context.args[0].lower()
    for uid, data in users_db.items():
        if data['username'].lower() == target_user:
            data['requests_surv'] += 50
            await update.message.reply_text(f"🔥 {target_user} получил +50 запросов выживания!")
            return

async def list_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📜 **СПИСОК КОМАНД**\n\n"
        "👤 **Для всех:**\n"
        "/start - Запуск\n"
        "/list - Список команд\n\n"
        "👑 **Для Администратора:**\n"
        "/setadmin @user - Выдать админку\n"
        "/setvip @user - Выдать VIP\n"
        "/setgod @user - Выдать GOD\n"
        "/delete @user - Забрать подписку\n"
        "/ban [1h/1d/ip] @user - Бан\n"
        "/unban @user - Разбан\n"
        "/give @user - +50 обычных запросов\n"
        "/gives @user - +50 запросов выживания"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    if user_id not in users_db: return
    user_data = users_db[user_id]

    if user_data['ban_until'] and datetime.now() < user_data['ban_until']:
        await update.message.reply_text(f"🚫 Вы забанены до {user_data['ban_until']}")
        return

    if text == "🎭 Режим Выживших: ВКЛ":
        if user_data['status'] == 'user':
            await update.message.reply_text("❌ Режим выживания запрещен для обычных юзеров! Купи VIP или GOD.")
            return
        user_data['mode'] = 'roleplay'
        await update.message.reply_text("✅ Режим Выживших: ВКЛ")
        return
    elif text == "🤖 Обычный режим: ВКЛ":
        user_data['mode'] = 'normal'
        await update.message.reply_text("✅ Обычный режим: ВКЛ")
        return
    elif text == "💎 Подписки":
        subs_text = (
            "💎 **ПОДПИСКИ**\n\n"
            "🆓 **Test** - 1д бесплатно, 50 запр. (Обычный)\n"
            "🌟 **VIP (20р)** - 30д, 100 запр/день + 10 запр. Выживание\n"
            "⚡ **GOD (50р)** - Безлим обычный + 50 запр. Выживание/день\n\n"
            "👉 Пиши @nodokc"
        )
        await update.message.reply_text(subs_text, parse_mode='Markdown')
        return
    elif text == "🆓 Получить Test":
        user_data['status'] = 'user'
        user_data['requests_ai'] = 50
        await update.message.reply_text("✅ Тестовый период активирован! Тебе начислено 50 обычных запросов. Режим выживания недоступен.")
        return

    # Логика лимитов
    status = user_data['status']
    mode = user_data.get('mode', 'normal')

    if mode == 'roleplay':
        if status == 'user':
            await update.message.reply_text("❌ Режим выживания запрещен для обычных юзеров!")
            return
        elif status == 'vip':
            if user_data['requests_surv'] <= 0:
                await update.message.reply_text("❌ Лимит Выживания исчерпан (10/день).")
                return
            user_data['requests_surv'] -= 1
        elif status == 'god':
            if user_data['requests_surv'] <= 0: user_data['requests_surv'] = 50
            user_data['requests_surv'] -= 1
    else:
        if status == 'user':
            if user_data['requests_ai'] <= 0:
                await update.message.reply_text("❌ Запросы закончились! Купи подписку у @nodokc.")
                return
            user_data['requests_ai'] -= 1
        elif status == 'vip':
            if user_data['requests_ai'] <= 0:
                await update.message.reply_text("❌ Лимит 100 запросов исчерпан.")
                return
            user_data['requests_ai'] -= 1

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    messages = []
    if mode == 'roleplay':
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    else:
        messages.append({"role": "system", "content": "You are a helpful AI assistant. Answer in Russian."})

    messages.extend(user_data['history'])
    user_msg = f"Village: {text}" if mode == 'roleplay' else text
    messages.append({"role": "user", "content": user_msg})

    try:
        response = requests.post(OLLAMA_URL, json={"model": OLLAMA_MODEL, "messages": messages, "stream": False}, timeout=120)
        if response.status_code == 200:
            answer = response.json().get('message', {}).get('content', 'Ошибка.')
            user_data['history'].append({"role": "user", "content": user_msg})
            user_data['history'].append({"role": "assistant", "content": answer})
            if len(user_data['history']) > 20: user_data['history'] = user_data['history'][-20:]
            await update.message.reply_text(answer)
        else:
            await update.message.reply_text(f"Ошибка сервера: {response.status_code}")
    except Exception as e:
        await update.message.reply_text(f"Критическая ошибка: {str(e)}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('setadmin', set_admin))
    application.add_handler(CommandHandler('setvip', set_vip))
    application.add_handler(CommandHandler('setgod', set_god))
    application.add_handler(CommandHandler('delete', delete_sub))
    application.add_handler(CommandHandler('ban', ban_user))
    application.add_handler(CommandHandler('unban', unban_user))
    application.add_handler(CommandHandler('give', give_reqs))
    application.add_handler(CommandHandler('gives', gives_reqs))
    application.add_handler(CommandHandler('list', list_commands))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("SaaS-BOT V3.0 PERFECT EDITION STARTED!")
    application.run_polling()
