import asyncio
import re
import easyocr
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from playwright.async_api import async_playwright

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = 'YOUR_BOT_TOKEN'
ADMIN_ID = 12345678  # Твой ID
CHANNEL_URL = 'bulldrop_standoff2'
CASE_URL = "https://bulldrop.net/case/название_кейса" # Укажи нужный кейс

reader = easyocr.Reader(['en'])
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class AuthState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_otp = State()

# Глобальные переменные для работы браузера
browser_instance = None
context_instance = None
page_instance = None

async def init_browser():
    global browser_instance, context_instance, page_instance
    pw = await async_playwright().start()
    browser_instance = await pw.chromium.launch(headless=True) # Поставь False для отладки
    context_instance = await browser_instance.new_context()
    page_instance = await context_instance.new_page()

@dp.message(Command("start"), F.from_user.id == ADMIN_ID)
async def cmd_start(message: types.Message, state: FSMContext):
    await init_browser()
    await message.answer("🛠 Введите номер телефона для Bulldrop (+7...):")
    await state.set_state(AuthState.waiting_for_phone)

@dp.message(AuthState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await page_instance.goto("https://bulldrop.net/login")
    await page_instance.fill('input[type="tel"]', message.text)
    await page_instance.click('button.login-submit') # Проверь селектор кнопки
    await message.answer("📟 Код из SMS:")
    await state.set_state(AuthState.waiting_for_otp)

@dp.message(AuthState.waiting_for_otp)
async def process_otp(message: types.Message, state: FSMContext):
    await page_instance.fill('input.otp-input', message.text)
    await page_instance.click('button.confirm-button')
    await asyncio.sleep(3) # Ждем прогрузки профиля
    await message.answer("✅ Авторизация завершена. Бот в режиме ожидания промокодов.")
    await state.clear()

@dp.channel_post(F.chat.username == CHANNEL_URL, F.photo)
async def handle_promo_photo(message: types.Message):
    if not page_instance: return

    # 1. Получаем фото и текст
    file = await bot.get_file(message.photo[-1].file_id)
    photo_bytes = await bot.download_file(file.file_path)
    results = reader.readtext(photo_bytes.read(), detail=0)
    full_text = " ".join(results)
    
    # 2. Ищем промокод
    match = re.search(r'[A-Z0-9]{5,12}', full_text)
    if match:
        code = match.group(0)
        await bot.send_message(ADMIN_ID, f"🔍 Вижу код: `{code}`. Активирую...")
        
        try:
            # 3. Переход на кейс и ввод
            await page_instance.goto(CASE_URL)
            await page_instance.fill('input#promo_input', code) # Селектор поля промокода
            await page_instance.click('button#open_case') # Селектор кнопки открытия
            
            # 4. Ожидание результата
            # Ждем появления названия предмета (селектор нужно уточнить в F12)
            drop_selector = ".modal-drop-name" 
            await page_instance.wait_for_selector(drop_selector, timeout=15000)
            drop_item = await page_instance.inner_text(drop_selector)
            
            await bot.send_message(ADMIN_ID, f"🎉 Кейс открыт ({code})\n🎁 Дроп: **{drop_item}**")
            
        except Exception as e:
            await bot.send_message(ADMIN_ID, f"❌ Ошибка при открытии: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
