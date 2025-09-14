# پایه: Python 3.11
FROM python:3.11-slim

# نصب Chromium و ابزارهای مورد نیاز
RUN apt-get update && apt-get install -y \
    chromium chromium-driver wget unzip curl \
    && rm -rf /var/lib/apt/lists/*

# به‌روزرسانی pip
RUN python -m pip install --upgrade pip

# تنظیم Chrome در حالت Headless
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_DRIVER=/usr/bin/chromedriver

# مسیر کاری پروژه داخل Docker
WORKDIR /app

# کپی فایل requirements و نصب کتابخانه‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کل فایل‌های پروژه
COPY . .

# اجرای ربات
CMD ["python", "bot.py"]
