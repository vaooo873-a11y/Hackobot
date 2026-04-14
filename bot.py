cat > ~/mail_bot_final.py << 'EOF'
#!/usr/bin/env python3
import requests
import time
import re
import json
import os
from datetime import datetime, date

# ===== ТВОИ ДАННЫЕ =====
BOT_TOKEN = "8587539177:AAEvuEtb8u77cWJdtpIY-mzjXOMk-FHUgSQ"
ADMIN_ID = "8195563239"  # ТВОЙ Telegram ID - ТЫ АДМИН!
ADMIN_USERNAME = "nodokc"
# =======================

API = "https://api.mail.tm"
session = requests.Session()
session.verify = False

# Файлы
VIP_FILE = "/sdcard/mail_vip_users.json"
MAIL_FILE = "/sdcard/mail_users_data.json"
STATS_FILE = "/sdcard/mail_stats.json"
PROCESSED_FILE = "/sdcard/processed_ids.txt"

def load_vip():
    if os.path.exists(VIP_FILE):
        with open(VIP_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_vip(vip):
    with open(VIP_FILE, 'w') as f:
        json.dump(vip, f)

def load_mails():
    if os.path.exists(MAIL_FILE):
        with open(MAIL_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_mails(mails):
    with open(MAIL_FILE, 'w') as f:
        json.dump(mails, f)

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_stats(stats):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f)

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            return set(f.read().splitlines())
    return set()

def save_processed(processed_id):
    with open(PROCESSED_FILE, 'a') as f:
        f.write(str(processed_id) + '\n')

def is_vip(user_id):
    vip = load_vip()
    user_id_str = str(user_id)
    if user_id_str in vip:
        expiry = vip[user_id_str].get('expiry')
        if expiry and expiry > time.time():
            return True
        elif expiry:
            del vip[user_id_str]
            save_vip(vip)
            return False
    return False

def check_limit(user_id):
    if is_vip(user_id):
        return True, 999999
    
    stats = load_stats()
    user_id_str = str(user_id)
    today = str(date.today())
    
    if user_id_str not in stats:
        stats[user_id_str] = {'last_date': today, 'count': 0}
        save_stats(stats)
    
    if stats[user_id_str]['last_date'] != today:
        stats[user_id_str] = {'last_date': today, 'count': 0}
        save_stats(stats)
    
    count = stats[user_id_str]['count']
    if count >= 2:
        return False, 0
    return True, 2 - count

def increment_usage(user_id):
    if is_vip(user_id):
        return
    stats = load_stats()
    user_id_str = str(user_id)
    today = str(date.today())
    if user_id_str not in stats or stats[user_id_str]['last_date'] != today:
        stats[user_id_str] = {'last_date': today, 'count': 0}
    stats[user_id_str]['count'] += 1
    save_stats(stats)

def get_remaining(user_id):
    if is_vip(user_id):
        return "∞ (VIP)"
    stats = load_stats()
    user_id_str = str(user_id)
    today = str(date.today())
    if user_id_str not in stats or stats[user_id_str]['last_date'] != today:
        return 2
    used = stats[user_id_str]['count']
    return max(0, 2 - used)

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Ошибка: {e}")

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    try:
        resp = requests.get(url, params=params, timeout=35)
        return resp.json().get("result", [])
    except:
        return []

def create_account(user_id):
    try:
        resp = session.get(f"{API}/domains")
        domains = resp.json()['hydra:member']
        domain = domains[0]['domain']
        import random
        name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
        email = f"{name}@{domain}"
        password = "pass" + ''.join(random.choices('0123456789', k=6))
        resp = session.post(f"{API}/accounts", json={"address": email, "password": password})
        if resp.status_code != 201:
            return None, None, None
        resp = session.post(f"{API}/token", json={"address": email, "password": password})
        token = resp.json().get('token')
        mails = load_mails()
        mails[str(user_id)] = {'email': email, 'password': password, 'token': token}
        save_mails(mails)
        return email, password, token
    except:
        return None, None, None

def get_user_mail(user_id):
    mails = load_mails()
    return mails.get(str(user_id))

def login_to_mail(user_id, email, password):
    try:
        resp = session.post(f"{API}/token", json={"address": email, "password": password})
        if resp.status_code != 200:
            return None
        token = resp.json().get('token')
        mails = load_mails()
        mails[str(user_id)] = {'email': email, 'password': password, 'token': token}
        save_mails(mails)
        return token
    except:
        return None

def get_messages(token):
    if not token:
        return []
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = session.get(f"{API}/messages?page=1&itemsPerPage=50", headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        return resp.json().get('hydra:member', [])
    except:
        return []

def read_message(token, msg_id):
    if not token:
        return None
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = session.get(f"{API}/messages/{msg_id}", headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        return resp.json()
    except:
        return None

def extract_codes(text):
    if not text or not isinstance(text, str):
        return []
    codes = re.findall(r'\b\d{4,8}\b', text)
    alnum = re.findall(r'\b[A-Z0-9]{4,10}\b', text)
    return list(set(codes + alnum))

def delete_all_messages(token):
    if not token:
        return 0
    headers = {"Authorization": f"Bearer {token}"}
    messages = get_messages(token)
    count = 0
    for msg in messages:
        try:
            resp = session.delete(f"{API}/messages/{msg['id']}", headers=headers)
            if resp.status_code == 204:
                count += 1
        except:
            pass
    return count

def is_admin(user_id):
    return str(user_id) == ADMIN_ID

def give_vip(user_id, days=30):
    vip = load_vip()
    user_id_str = str(user_id)
    expiry = time.time() + (days * 86400)
    vip[user_id_str] = {'expiry': expiry, 'granted_by': ADMIN_ID, 'date': str(date.today())}
    save_vip(vip)
    return f"✅ VIP статус выдан на {days} дней!"

def remove_vip(user_id):
    vip = load_vip()
    user_id_str = str(user_id)
    if user_id_str in vip:
        del vip[user_id_str]
        save_vip(vip)
        return "✅ VIP статус снят"
    return "❌ У этого пользователя нет VIP"

def show_stats():
    vip = load_vip()
    stats = load_stats()
    mails = load_mails()
    text = "📊 <b>СТАТИСТИКА</b>\n\n"
    text += f"👥 Пользователей: {len(mails)}\n"
    text += f"⭐ VIP: {len(vip)}\n"
    if vip:
        text += "\n<b>VIP список:</b>\n"
        for uid in vip:
            user_mail = mails.get(uid, {}).get('email', 'нет почты')
            text += f"• {uid} - {user_mail}\n"
    return text

def handle_command(user_id, cmd, args):
    limit_commands = ['/inbox', '/read', '/code']
    if cmd in limit_commands:
        can_use, _ = check_limit(user_id)
        if not can_use:
            remaining = get_remaining(user_id)
            return (f"❌ <b>Лимит исчерпан!</b>\n\n"
                   f"У тебя бесплатный тариф: 2 письма в день.\n"
                   f"Осталось сегодня: {remaining}\n\n"
                   f"⭐ Купи VIP: /subscription")
    
    if cmd in ['/start', '/help']:
        vip_status = "⭐ VIP" if is_vip(user_id) else "🆓 Free"
        remaining = get_remaining(user_id)
        return (f"📧 <b>Временная почта</b>\n\n"
               f"Твой статус: {vip_status}\n"
               f"Писем сегодня: {remaining}\n\n"
               "<b>Команды:</b>\n"
               "/new - Создать ящик\n"
               "/login email пароль - Войти\n"
               "/inbox - Список писем\n"
               "/read N - Прочитать\n"
               "/code - Ждать код\n"
               "/status - Информация\n"
               "/delete - Удалить всё\n"
               "/subscription - Купить VIP\n\n"
               f"👑 Админ: @{ADMIN_USERNAME}")
    
    elif cmd == "/subscription":
        return ("⭐ <b>VIP ПОДПИСКА</b>\n\n"
               "<b>Преимущества:</b>\n"
               "• Безлимит писем\n"
               "• Приоритет\n\n"
               f"💰 Цена: 100₽/месяц\n\n"
               f"📩 Купить: @{ADMIN_USERNAME}")
    
    elif cmd == "/new":
        email, pwd, token = create_account(user_id)
        if email:
            return (f"✅ <b>Ящик создан!</b>\n\n"
                   f"📧 <code>{email}</code>\n"
                   f"🔑 <code>{pwd}</code>\n\n"
                   f"⭐ Статус: {'VIP' if is_vip(user_id) else 'Free'}")
        return "❌ Ошибка"
    
    elif cmd == "/login":
        if len(args) < 2:
            return "❌ /login email пароль"
        token = login_to_mail(user_id, args[0], args[1])
        if token:
            return f"✅ Вход: {args[0]}"
        return "❌ Ошибка"
    
    elif cmd == "/status":
        mail_data = get_user_mail(user_id)
        if not mail_data:
            return "❌ Нет ящика. /new"
        msgs = get_messages(mail_data['token'])
        vip_status = "VIP" if is_vip(user_id) else "Free"
        remaining = get_remaining(user_id)
        return (f"📊 <b>Статус</b>\n\n"
               f"📧 {mail_data['email']}\n"
               f"📬 Писем: {len(msgs)}\n"
               f"⭐ {vip_status}\n"
               f"📅 Осталось: {remaining}")
    
    elif cmd == "/inbox":
        mail_data = get_user_mail(user_id)
        if not mail_data:
            return "❌ /new"
        msgs = get_messages(mail_data['token'])
        if not msgs:
            return "📭 Нет писем"
        increment_usage(user_id)
        result = f"📬 <b>{len(msgs)} писем</b>\n\n"
        for i, m in enumerate(msgs[:10], 1):
            subj = m.get('subject', '(без темы)')[:40]
            result += f"{i}. {subj}\n"
        if len(msgs) > 10:
            result += f"\n... ещё {len(msgs)-10}"
        result += "\n\n/read N"
        return result
    
    elif cmd == "/read":
        if not args:
            return "❌ /read 1"
        mail_data = get_user_mail(user_id)
        if not mail_data:
            return "❌ /new"
        try:
            num = int(args[0]) - 1
            msgs = get_messages(mail_data['token'])
            if num < 0 or num >= len(msgs):
                return "❌ Неверно"
            increment_usage(user_id)
            msg = read_message(mail_data['token'], msgs[num]['id'])
            if not msg:
                return "❌ Ошибка"
            subject = msg.get('subject', '(без темы)')
            from_addr = msg.get('from', {}).get('address', '?')
            text = msg.get('text', '')[:1000]
            codes = extract_codes(text)
            result = f"📨 <b>{subject}</b>\n\n📬 {from_addr}\n\n📄 {text}"
            if codes:
                result += f"\n\n🔑 <b>КОД: {codes[0]}</b>"
            return result
        except:
            return "❌ Ошибка"
    
    elif cmd == "/code":
        mail_data = get_user_mail(user_id)
        if not mail_data:
            return "❌ /new"
        seen = set()
        for _ in range(20):
            msgs = get_messages(mail_data['token'])
            for m in msgs:
                if m['id'] not in seen:
                    seen.add(m['id'])
                    full = read_message(mail_data['token'], m['id'])
                    if full:
                        codes = extract_codes(full.get('text', ''))
                        if codes:
                            increment_usage(user_id)
                            return f"🔑 <b>КОД: {codes[0]}</b>"
            time.sleep(3)
        return "⏰ Код не пришёл"
    
    elif cmd == "/delete":
        mail_data = get_user_mail(user_id)
        if not mail_data:
            return "❌ Нет ящика"
        count = delete_all_messages(mail_data['token'])
        return f"🗑️ Удалено {count} писем"
    
    # АДМИН КОМАНДЫ (только ты)
    elif cmd == "/admin" and is_admin(user_id):
        return ("👑 <b>АДМИН ПАНЕЛЬ</b>\n\n"
               "/stats - Статистика\n"
               "/givevip ID дни - Выдать VIP\n"
               "/removevip ID - Снять VIP\n"
               "/broadcast текст - Рассылка")
    
    elif cmd == "/stats" and is_admin(user_id):
        return show_stats()
    
    elif cmd == "/givevip" and is_admin(user_id):
        if len(args) < 2:
            return "❌ /givevip 123456789 30"
        try:
            target_id = args[0]
            days = int(args[1])
            result = give_vip(target_id, days)
            send_telegram(target_id, f"🎉 <b>Тебе выдан VIP на {days} дней!</b>\n\nБезлимит писем активирован.")
            return result
        except:
            return "❌ Ошибка"
    
    elif cmd == "/removevip" and is_admin(user_id):
        if not args:
            return "❌ /removevip ID"
        result = remove_vip(args[0])
        send_telegram(args[0], f"❌ <b>VIP статус снят</b>\n\nТеперь 2 письма в день.")
        return result
    
    elif cmd == "/broadcast" and is_admin(user_id):
        if not args:
            return "❌ /broadcast текст"
        text = ' '.join(args)
        mails = load_mails()
        sent = 0
        for uid in mails:
            try:
                send_telegram(uid, f"📢 <b>РАССЫЛКА</b>\n\n{text}")
                sent += 1
                time.sleep(0.1)
            except:
                pass
        return f"✅ Отправлено {sent} пользователям"
    
    return None

def main():
    print("🤖 БОТ ЗАПУЩЕН!")
    print(f"👑 Твой ID: {ADMIN_ID} - ТЫ АДМИН!")
    print("✅ Двойной ответ исправлен")
    
    last_update_id = 0
    processed_ids = load_processed()
    
    while True:
        try:
            updates = get_updates(last_update_id + 1 if last_update_id else None)
            
            for update in updates:
                update_id = update['update_id']
                
                # Пропускаем уже обработанные
                if str(update_id) in processed_ids:
                    continue
                
                processed_ids.add(str(update_id))
                save_processed(update_id)
                last_update_id = update_id
                
                if 'message' in update:
                    msg = update['message']
                    user_id = str(msg['from']['id'])
                    text = msg.get('text', '')
                    
                    if text:
                        parts = text.split()
                        cmd = parts[0].lower()
                        args = parts[1:] if len(parts) > 1 else []
                        
                        print(f"📨 {user_id}: {cmd}")
                        response = handle_command(user_id, cmd, args)
                        if response:
                            send_telegram(user_id, response)
            
            time.sleep(1)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
EOF
python ~/mail_bot_final.py
