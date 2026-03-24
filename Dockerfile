# Используем образ с предустановленным Playwright и Python
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Устанавливаем системные зависимости для сборки тяжелых либ
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Сначала обновляем инструменты сборки, потом ставим либы
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Установка браузера и его зависимостей
RUN playwright install chromium
RUN playwright install-deps

CMD ["python", "main.py"]
