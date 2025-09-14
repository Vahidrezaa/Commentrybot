# Dockerfile
FROM python:3.11-slim
# نصب Chromium و ابزارهای مورد نیاز
RUN apt-get update && apt-get install -y \
    chromium chromium-driver wget unzip curl \
    && rm -rf /var/lib/apt/lists/*

# تنظیم Chrome در حالت Headless
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_DRIVER=/usr/bin/chromedriver

# کپی فایل‌های پروژه
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# اجرای ربات
CMD ["python", "bot.py"]
