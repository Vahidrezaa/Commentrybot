# استفاده از ایمیج پایه پایتون
FROM python:3.11-slim

# تنظیم دایرکتوری کاری
WORKDIR /app

# کپی requirements.txt و نصب وابستگی‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کد پروژه
COPY fotmob_bot.py .

# تنظیم متغیرهای محیطی (توکن و آیدی کانال بعداً باید ست بشن)
ENV BOT_TOKEN=your_bot_token
ENV CHANNEL_ID=@your_channel_id

# اجرای بات
CMD ["python", "fotmob_bot.py"]
