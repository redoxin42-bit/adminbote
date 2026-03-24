# Используем образ с предустановленным Playwright и Python
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Установка системных зависимостей для сборки
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаем пользователя 'user' с UID 1000 (требование Hugging Face)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Устанавливаем рабочую директорию
WORKDIR $HOME/app

# Копируем все файлы проекта и даем права пользователю
COPY --chown=user . $HOME/app

# Обновляем pip и ставим зависимости
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Установка браузера Chromium (только бинарники)
RUN playwright install chromium
RUN playwright install-deps

# Открываем порт 7860 (стандарт для HF)
EXPOSE 7860

# Запуск бота
CMD ["python", "main.py"]
