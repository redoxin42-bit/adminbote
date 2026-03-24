import asyncio
import re
import easyocr
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from playwright.async_api import async_playwright

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8535244495:AAGeAGzpP3BNMkrrL8pvxNwVi_0UPh8hbus'
ADMIN_ID = 8624430245  # Твой ID вставлен
CHANNEL_USERNAME = 'bulldrop_standoff2'
BASE_URL = "https://bulldrop.net/case/"

# МАКСИМАЛЬНЫЙ СПИСОК КЕЙСОВ ДЛЯ ТОЧНОГО ПОПАДАНИЯ
CASE_MAP = {
    # ПЕРСОНАЖИ / КИНО
    "ШЕЛБИ": "shelby", "SHELBY": "shelby", "THOMAS": "shelby", "ТОМАС": "shelby",
    "ДЖОКЕР": "joker", "JOKER": "joker",
    "УЭНСДЕЙ": "wednesday", "WEDNESDAY": "wednesday",
    
    # АНИМЕ / ТЯНКИ / ВАЙФУ
    "АНИМЕ": "anime-pack", "ANIME": "anime-pack",
    "ТЯН": "waifu-case", "WAIFU": "waifu-case", "ТЯНОЧКИ": "waifu-case",
    "ХЕНТАЙ": "hentai-edition", "HENTAI": "hentai-edition",
    "ДЕВОЧКИ": "girls-power", "GIRLS": "girls-power",
    "ЗЕНИТЦУ": "zenitsu", "ZENITSU": "zenitsu",
    "НАРУТО": "naruto", "NARUTO": "naruto", "ТЯНКИ": "waifu-case",
    
    # СТИХИИ
    "ОГОНЬ": "fire-spirit", "FIRE": "fire-spirit",
    "ВОДА": "water-spirit", "WATER": "water-spirit",
    "ЗЕМЛЯ": "earth-spirit", "EARTH": "earth-spirit",
    "ВОЗДУХ": "air-spirit", "AIR": "air-spirit",
    "СТИХИИ": "elements",
    
    # ОРУЖИЕ / НОЖИ
    "НОЖ": "knife-case", "KNIFE": "knife-case",
    "КЕРАМБИТ": "karambit", "KARAMBIT": "karambit",
    "М9": "m9-bayonet", "M9": "m9-bayonet",
    "БАБОЧКА": "butterfly", "BUTTERFLY": "butterfly",
    "ПЕРЧАТКИ": "gloves", "GLOVES": "gloves",
    "АРКАНА": "arcane", "ARCANE": "arcane",
    
    # КОЛЛЕКЦИИ / ТЕМАТИКА
    "ГАММА": "gamma", "GAMMA": "gamma",
    "АЗИМОВ": "asiimov", "ASIMOV": "asiimov",
    "ДРАКОН": "dragon-lore", "DRAGON": "dragon-lore",
    "ЗИМА": "winter", "WINTER": "winter",
    "ФЕНИКС": "phoenix", "PHOENIX": "phoenix",
    "СЕКРЕТ": "secret", "SECRET": "secret",
    
    # БЕСПЛАТНЫЕ / БОНУСЫ
    "ЕЖЕДНЕВНЫЙ": "daily", "DAILY": "daily",
    "ХАЛЯВА": "free-box", "FREE": "free-box",
    "БОНУС": "bonus"
}

reader = easyocr.Reader(['en', 'ru'])
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class AuthState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_otp = State()

browser, context, page = None, None, None

async def init_browser():
    global browser, context, page
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
    context = await browser.new_context()
    page = await context.new_page()

@dp.message(Command("start"), F.from_user.id == ADMIN_ID)
async def cmd_start(message: types.Message, state: FSMContext):
    if not browser: await init_browser()
    await message.answer("🛠 Бот активен. Введи номер телефона для входа в Bulldrop (+7...):")
    await state.set_state(AuthState.waiting_for_phone)

@dp.message(AuthState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await page.goto("https://bulldrop.net/login")
    await page.fill('input[type="tel"]', message.text)
    await page.click('button.login-submit') 
    await message.answer("📟 Введи код подтверждения (из СМС или звонка):")
    await state.set_state(AuthState.waiting_for_otp)

@dp.message(AuthState.waiting_for_otp)
async def process_otp(message: types.Message, state: FSMContext):
    await page.fill('input.otp-input', message.text)
    await page.click('button.confirm-button')
    await asyncio.sleep(5)
    await message.answer("✅ Авторизация успешна! Мониторинг канала запущен.")
    await state.clear()

@dp.channel_post(F.chat.username == CHANNEL_USERNAME, F.photo)
async def handle_promo_photo(message: types.Message):
    if not page: return
    
    # 1. Распознавание текста
    file = await bot.get_file(message.photo[-1].file_id)
    photo_bytes = await bot.download_file(file.file_path)
    results = reader.readtext(photo_bytes.read(), detail=0)
    full_text = " ".join(results).upper()
    
    # 2. Поиск промокода
    code_match = re.search(r'[A-Z0-9]{5,15}', full_text)
    if not code_match: return
    code = code_match.group(0)

    # 3. Определение кейса по словарю или авто-подбор
    target_slug = "daily" 
    found_name = "DEFAULT"
    
    for key in CASE_MAP:
        if key in full_text:
            target_slug = CASE_MAP[key]
            found_name = key
            break

    final_url = f"{BASE_URL}{target_slug}"
    await bot.send_message(ADMIN_ID, f"🚀 Вижу код: `{code}`\n📦 Кейс: `{found_name}`\nАктивирую...")

    try:
        await page.goto(final_url)
        await page.wait_for_selector('input.promo-field', timeout=10000)
        await page.fill('input.promo-field', code)
        await page.click('button.open-case-btn')
        
        # Ожидание результата открытия
        drop_selector = ".drop-item-name" 
        await page.wait_for_selector(drop_selector, timeout=20000)
        item = await page.inner_text(drop_selector)
        await bot.send_message(ADMIN_ID, f"🎉 Кейс {found_name} успешно открыт!\n🎁 Выпало: **{item}**")
    except Exception as e:
        await bot.send_message(ADMIN_ID, f"❌ Ошибка на кейсе {found_name}: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
