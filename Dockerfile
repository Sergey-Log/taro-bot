FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .

# Установка Python-зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание папки для базы данных
RUN mkdir -p /app/data

# Переменная окружения для пути к БД
ENV DATABASE_PATH=/app/data/tarot_bot.db
ENV PYTHONUNBUFFERED=1

# Команда запуска
CMD ["python", "bot.py"]