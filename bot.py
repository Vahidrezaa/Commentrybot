# پروژه کامل ربات تلگرام گزارش زنده فوت‌موب با Dockerfile و آماده اجرا روی Railway

# bot.py
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from deep_translator import GoogleTranslator
from telegram import Bot

# خواندن متغیرهای محیطی
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')
FUTMOB_URL = os.environ.get('FUTMOB_URL')
CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', 20))  # ثانیه

# راه‌اندازی ربات و مترجم
bot = Bot(token=TELEGRAM_TOKEN)

# ذخیره متن‌های ارسال شده
sent_texts = set()

# تنظیمات Chrome Headless
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-extensions')
driver = webdriver.Chrome(options=options)

# تابع استخراج متن‌ها
def fetch_live_texts():
    driver.get(FUTMOB_URL)
    time.sleep(5)  # منتظر بارگذاری کامل صفحه

    # استخراج رویدادها از تب Ticker
    try:
        events = driver.find_elements(By.CSS_SELECTOR, 'li.ticker-event')  # نمونه CSS Selector
        texts = []
        for e in events:
            try:
                time_elem = e.find_element(By.CLASS_NAME, 'minute').text
                desc_elem = e.find_element(By.CLASS_NAME, 'description').text
                full_text = f"{time_elem} - {desc_elem}"
                texts.append(full_text)
            except:
                continue
        return texts
    except Exception as err:
        print('Error fetching live texts:', err)
        return []

# حلقه اصلی
try:
    while True:
        live_texts = fetch_live_texts()
        for text in live_texts:
            if text not in sent_texts:
                sent_texts.add(text)
                translated = GoogleTranslator(source='en', target='fa').translate(text)
                bot.send_message(chat_id=CHANNEL_ID, text=translated)
        time.sleep(CHECK_INTERVAL)
except KeyboardInterrupt:
    print("ربات متوقف شد.")
finally:
    driver.quit()
