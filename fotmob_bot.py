import re
import requests
import threading
import time
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, Filters, CallbackContext
from deep_translator import GoogleTranslator
from typing import Dict, Set, Any

# تنظیمات
BOT_TOKEN = 'YOUR_BOT_TOKEN'  # توکن بات
CHANNEL_ID = '@your_channel_id'  # آیدی کانال
CHECK_INTERVAL = 30  # چک هر ۳۰ ثانیه
MAX_MESSAGE_LENGTH = 4000  # حاشیه ایمنی برای طول پیام

bot = Bot(token=BOT_TOKEN)
translator = GoogleTranslator(source='en', target='fa')

# دیکشنری برای match_id: (thread, seen_events set, home_team, away_team, is_active)
active_matches: Dict[str, tuple[threading.Thread, Set[str], str, str, bool]] = {}

def extract_match_id(url: str) -> str:
    """استخراج match_id از لینک FotMob"""
    match = re.search(r'/match/(\d+)|#(\d+)', url)
    if match:
        return match.group(1) or match.group(2)
    raise ValueError("لینک معتبر FotMob نیست! (فرمت: /match/123456 یا #123456) مثال: https://www.fotmob.com/matches/...#123456")

def fetch_match_data(match_id: str) -> Dict[str, Any]:
    """گرفتن داده‌های matchDetails از API FotMob"""
    url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.fotmob.com/'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise Exception(f"خطا در گرفتن داده: {str(e)}")

def translate_text(text: str) -> str:
    """ترجمه به فارسی با deep-translator"""
    if not text.strip():
        return ""
    try:
        return translator.translate(text)
    except Exception as e:
        print(f"خطای ترجمه: {e}")
        return text

def get_home_away_names(data: Dict[str, Any]) -> tuple[str, str]:
    """گرفتن نام تیم‌ها"""
    content = data.get('content', {})
    home = content.get('homeTeam', {}).get('name', 'تیم میزبان')
    away = content.get('awayTeam', {}).get('name', 'تیم مهمان')
    return translate_text(home), translate_text(away)

def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """تقسیم پیام طولانی به بخش‌های کوچکتر"""
    if len(text) <= max_length:
        return [text]
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        split_point = text[:max_length].rfind('\n')
        if split_point == -1:
            split_point = max_length
        parts.append(text[:split_point])
        text = text[split_point:].lstrip()
    return parts

def format_commentary_update(data: Dict[str, Any], seen_events: Set[str], home: str, away: str) -> tuple[str, Set[str]]:
    """فرمت آپدیت commentary جدید"""
    content = data.get('content', {})
    events = content.get('events', []) or []
    score = f"{content.get('homeScore', {}).get('current', 0)} - {content.get('awayScore', {}).get('current', 0)}"

    new_events = []
    new_seen = set(seen_events)
    update_text = f"🔴 گزارش زنده: {home} vs {away} | نتیجه: {score}\n\n"

    for event in reversed(events):
        event_id = str(event.get('id', ''))
        if event_id not in seen_events and event.get('text'):
            minute = event.get('minute', '?')
            event_type = event.get('eventType', '')
            text = event.get('text', '')

            translated_text = translate_text(text)
            side = '🏠' if event.get('isHome', False) else '✈️'
            emoji = get_event_emoji(event_type)
            new_events.append(f"{emoji} [{minute}'] {side} {translated_text}")
            new_seen.add(event_id)

    if new_events:
        update_text += "📢 رویدادهای جدید:\n" + "\n".join(reversed(new_events))
    else:
        update_text += "⏳ در حال انتظار برای رویداد جدید..."

    return update_text, new_seen

def get_event_emoji(event_type: str) -> str:
    """ایموجی بر اساس نوع رویداد"""
    emojis = {
        'goal': '⚽', 'goal-penalty': '⚽', 'yellowcard': '🟨', 'redcard': '🟥',
        'substitution': '🔄', 'offside': '🚩', 'var': '📹', 'corner': '🏃‍♂️',
        'freekick': '🎯', 'freekick-crossed': '🎯'
    }
    return emojis.get(event_type, '📝')

def send_live_update(match_id: str, initial_seen: Set[str], home: str, away: str):
    """ارسال آپدیت زنده commentary"""
    seen_events = initial_seen.copy()
    while active_matches.get(match_id, [None, None, None, None, False])[4]:
        try:
            data = fetch_match_data(match_id)
            update_text, seen_events = format_commentary_update(data, seen_events, home, away)
            for part in split_message(update_text):
                bot.send_message(chat_id=CHANNEL_ID, text=part, parse_mode='HTML')
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"خطا در آپدیت {match_id}: {e}")
            time.sleep(CHECK_INTERVAL * 5)

def start(update: Update, context: CallbackContext):
    """کامند /start <لینک>"""
    if not context.args:
        update.message.reply_text("لطفاً لینک بازی FotMob رو بعد از /start بفرستید.\nمثال: /start https://www.fotmob.com/matches/...#123456")
        return

    url = context.args[0]
    try:
        match_id = extract_match_id(url)
        if match_id in active_matches:
            update.message.reply_text(f"بازی با ID {match_id} قبلاً در حال مانیتورینگ است!")
            return

        data = fetch_match_data(match_id)
        initial_events = data.get('content', {}).get('events', []) or []
        initial_seen = {str(e.get('id', '')) for e in initial_events if e.get('id') and e.get('text')}
        home, away = get_home_away_names(data)

        thread = threading.Thread(target=send_live_update, args=(match_id, initial_seen, home, away), daemon=True)
        thread.start()
        active_matches[match_id] = (thread, initial_seen, home, away, True)

        update.message.reply_text(f"✅ مانیتورینگ commentary بازی {home} vs {away} (ID: {match_id}) شروع شد. آپدیت‌ها به {CHANNEL_ID} می‌ره.")
        
        update_text, _ = format_commentary_update(data, initial_seen, home, away)
        for part in split_message(update_text):
            bot.send_message(chat_id=CHANNEL_ID, text=part)
        
    except Exception as e:
        update.message.reply_text(f"❌ خطا: {str(e)}\nنکته: لینک باید معتبر و از بازی جاری باشه.")

def stop(update: Update, context: CallbackContext):
    """کامند /stop <match_id>"""
    if not context.args:
        update.message.reply_text("لطفاً match_id رو بعد از /stop بفرستید.\nمثال: /stop 123456")
        return

    match_id = context.args[0]
    if match_id not in active_matches:
        update.message.reply_text(f"بازی با ID {match_id} در حال مانیتورینگ نیست!")
        return

    thread, seen_events, home, away, _ = active_matches[match_id]
    active_matches[match_id] = (thread, seen_events, home, away, False)
    update.message.reply_text(f"🛑 مانیتورینگ بازی {home} vs {away} (ID: {match_id}) متوقف شد.")

def status(update: Update, context: CallbackContext):
    """کامند /status"""
    if not active_matches:
        update.message.reply_text("هیچ بازی‌ای در حال مانیتورینگ نیست.")
        return

    response = "📊 بازی‌های در حال مانیتورینگ:\n"
    for match_id, (_, _, home, away, is_active) in active_matches.items():
        status = "فعال" if is_active else "متوقف"
        response += f"- {home} vs {away} (ID: {match_id}, وضعیت: {status})\n"
    update.message.reply_text(response)

def help_command(update: Update, context: CallbackContext):
    """کامند /help"""
    response = (
        "📖 راهنمای بات:\n"
        "/start <لینک> - شروع مانیتورینگ commentary بازی (لینک FotMob)\n"
        "/stop <match_id> - توقف مانیتورینگ یه بازی\n"
        "/status - نمایش بازی‌های در حال مانیتورینگ\n"
        "/help - نمایش این راهنما\n\n"
        "مثال لینک: https://www.fotmob.com/matches/...#123456"
    )
    update.message.reply_text(response)

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("help", help_command))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
