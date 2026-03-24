# Используем образ с Python и инструментами для Playwright
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Устанавливаем системные зависимости для сборки тяжелых библиотек
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Обновляем pip и ставим зависимости из списка
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Установка браузера Chromium и его системных библиотек
RUN playwright install chromium
RUN playwright install-deps

# Команда для запуска бота
CMD ["python", "main.py"]
