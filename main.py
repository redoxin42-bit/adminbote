import asyncio
import re
import easyocr
import threading
import logging
import gc
import os
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from playwright.async_api import async_playwright

# Настройка логирования для отслеживания ошибок в Render/Railway
logging.basicConfig(level=logging.INFO)

# --- FLASK СЕРВЕР (Для "оживления" хостинга) ---
app = Flask(__name__)
@app.route('/')
def health_check(): return "OK"

def run_flask():
    port = int(os.environ.get("PORT", 7860))
    app.run(host='0.0.0.0', port=port)

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8535244495:AAGeAGzpP3BNMkrrL8pvxNwVi_0UPh8hbus'
CHANNEL_USERNAME = 'bulldrop_standoff2'
BASE_URL = "https://bulldrop.net/case/"
ADMIN_ID = 8624430245

# Твоя "База" кейсов со всех скриншотов
CASE_MAP = {
    # Пацанский кодекс
    "ЖИГА": "zhiga", "СЕМКИ": "semki", "КЕПКА": "cap-case", "БАРСЕТКА": "waist-bag",
    "МАФИЯ": "mafia-case", "БРИГАДА": "brigada", "СЛОВО ПАЦАНА": "word-of-boy", "РЕШАЛА": "reshala",
    # Это база
    "БАЗА": "base-case", "КЛАССИКА": "classic-box", "ОЛДЫ ТУТ": "olds-here", "НАЧАЛО": "the-beginning",
    # Актуальное (и не очень)
    "ЧИЛЛОВЫЙ ПАРЕНЬ": "chill-guy", "ДИКИЙ ОГУРЕЦ": "wild-cucumber", "Я И МОЙ БРО": "me-and-bro", 
    "СКЕБОБ": "skebob", "БУ": "boo-case", "ОК ДЖАРВИС": "ok-jarvis", 
    "ОТЦОВСКИЙ МЕНТАЛИТЕТ": "dad-mentality", "ПОКОЙ В БОГАТСТВЕ": "rich-peace",
    # Любимые игры
    "DOTA 2": "dota-2", "MARVEL RIVALS": "marvel-rivals", "GTA V": "gta-v", 
    "FORTNITE": "fortnite", "VALORANT": "valorant",
    # Короли дорог
    "BMW M3": "bmw-m3", "CYBERTRUCK": "cybertruck", "SUPRA FF": "supra-ff", 
    "DODGE FF": "dodge-ff", "NISSAN FF2": "nissan-ff2", "G63": "g63-amg", 
    "FERRARI": "ferrari", "LAMBORGHINI": "lambo",
    # Камни превосходства
    "САПФИР": "sapphire", "РУБИН": "ruby", "ИЗУМРУД": "emerald", "ЭФЕРИОН": "etherion",
    # Легенды футбола и кино
    "НЕЙМАР": "neymar", "МБАППЕ": "mbappe", "РОНАЛДО": "ronaldo", "МЕССИ": "messi",
    "ЗИДАН": "zidane", "ЯШИН": "yashin", "МАРАДОНА": "maradona", "ПЕЛЕ": "pele",
    "ТАЙЛЕР ДЕРДЕН": "tyler-durden", "РАЙАН ГОСЛИНГ": "ryan-gosling", 
    "КАПИТАН ДЖЕК ВОРОБЕЙ": "jack-sparrow", "СКАЛА": "the-rock",
    # Грехи чародея
    "ПРОКЛЯТОЕ ВАРЕВО": "cursed-brew", "ЗОЛОТАЯ ПОГИБЕЛЬ": "golden-doom", 
    "ПОСЛЕДНИЙ УГОВОР": "last-deal", "ПЕРВОРОДНАЯ НАСТОЙКА": "original-tincture",
    # Разное
    "АНИМЕ": "anime-pack", "ТЯНОЧКИ": "waifu-case", "DAILY": "daily"
}

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
reader = None
browser, context, page = None, None, None

class AuthState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_otp = State()

async def init_browser():
    global browser, context, page
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    context = await browser.new_context()
    page = await context.new_page()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if not browser: await init_browser()
    await message.answer("🚀 Бот запущен! Введи номер телефона для Bulldrop (+7...):")
    await state.set_state(AuthState.waiting_for_phone)

@dp.message(AuthState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await page.goto("https://bulldrop.net/login")
    await page.fill('input[type="tel"]', message.text)
    await page.click('button.login-submit') 
    await message.answer("📟 Жду код из СМС:")
    await state.set_state(AuthState.waiting_for_otp)

@dp.message(AuthState.waiting_for_otp)
async def process_otp(message: types.Message, state: FSMContext):
    await page.fill('input.otp-input', message.text)
    await page.click('button.confirm-button')
    await asyncio.sleep(5)
    await message.answer("✅ Вход выполнен. Бот мониторит канал!")
    await state.clear()

@dp.channel_post(F.chat.username == CHANNEL_USERNAME, F.photo)
async def handle_promo_photo(message: types.Message):
    global reader
    if not page: return

    # Инициализация OCR с экономией памяти
    if reader is None:
        reader = easyocr.Reader(['en', 'ru'], gpu=False)

    file = await bot.get_file(message.photo[-1].file_id)
    photo_bytes = await bot.download_file(file.file_path)
    
    # Распознавание
    results = reader.readtext(photo_bytes.read(), detail=0)
    full_text = " ".join(results).upper()
    gc.collect() # Очистка после OCR

    code_match = re.search(r'[A-Z0-9]{5,15}', full_text)
    if not code_match: return
    code = code_match.group(0)

    # Поиск подходящего кейса
    target_slug = "daily" 
    for key, slug in CASE_MAP.items():
        if key in full_text:
            target_slug = slug
            break

    try:
        await page.goto(f"{BASE_URL}{target_slug}")
        await page.wait_for_selector('input.promo-field', timeout=7000)
        await page.fill('input.promo-field', code)
        await page.click('button.open-case-btn')
        await bot.send_message(ADMIN_ID, f"🎯 Активирован код `{code}` на кейс `{target_slug}`")
    except Exception as e:
        logging.error(f"Ошибка активации: {e}")
    finally:
        gc.collect() # Очистка после работы браузера

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
        except Exception as e:
            logging.error(f"Сеть: {e}") # Отлов ошибок типа ClientConnectorError
            await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
