import asyncio
import re
import os
import easyocr
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from playwright.async_api import async_playwright

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8535244495:AAGeAGzpP3BNMkrrL8pvxNwVi_0UPh8hbus'
ADMIN_ID = 0  # СЮДА ВПИШИ СВОЙ ID (Узнай у @userinfobot)
CHANNEL_USERNAME = 'bulldrop_standoff2'
CASE_URL = "https://bulldrop.net/case/название_кейса" # УКАЖИ ССЫЛКУ НА КЕЙС

reader = easyocr.Reader(['en'])
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class AuthState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_otp = State()

browser = None
context = None
page = None

async def init_browser():
    global browser, context, page
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
    context = await browser.new_context()
    page = await context.new_page()

@dp.message(Command("start"), F.from_user.id == ADMIN_ID)
async def cmd_start(message: types.Message, state: FSMContext):
    if not browser:
        await init_browser()
    await message.answer("🛠 Авторизация Bulldrop. Введи номер телефона (+7...):")
    await state.set_state(AuthState.waiting_for_phone)

@dp.message(AuthState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await page.goto("https://bulldrop.net/login")
    await page.fill('input[type="tel"]', message.text)
    await page.click('button.login-submit') # Проверь селектор кнопки на сайте
    await message.answer("📟 Введи код подтверждения из SMS:")
    await state.set_state(AuthState.waiting_for_otp)

@dp.message(AuthState.waiting_for_otp)
async def process_otp(message: types.Message, state: FSMContext):
    await page.fill('input.otp-input', message.text) # Проверь селектор поля
    await page.click('button.confirm-button')
    await asyncio.sleep(5)
    await message.answer("✅ Авторизация успешна! Мониторинг запущен.")
    await state.clear()

@dp.channel_post(F.chat.username == CHANNEL_USERNAME, F.photo)
async def handle_promo_photo(message: types.Message):
    if not page: return

    # Скачивание и чтение фото
    file = await bot.get_file(message.photo[-1].file_id)
    photo_bytes = await bot.download_file(file.file_path)
    results = reader.readtext(photo_bytes.read(), detail=0)
    full_text = " ".join(results)
    
    # Поиск промокода (латиница + цифры)
    match = re.search(r'[A-Z0-9]{5,15}', full_text)
    if match:
        code = match.group(0)
        await bot.send_message(ADMIN_ID, f"🔍 Найден код: `{code}`. Активирую...")
        
        try:
            await page.goto(CASE_URL)
            await page.fill('input.promo-field', code) # Проверь селектор поля промо
            await page.click('button.open-case-btn') # Проверь селектор кнопки
            
            # Ожидание дропа (ждем появления текста с названием предмета)
            drop_selector = ".drop-item-name" # Селектор названия предмета
            await page.wait_for_selector(drop_selector, timeout=20000)
            item_name = await page.inner_text(drop_selector)
            
            await bot.send_message(ADMIN_ID, f"✅ Кейс открыт ({code})\n🎁 Дроп: **{item_name}**")
        except Exception as e:
            await bot.send_message(ADMIN_ID, f"❌ Ошибка активации: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
