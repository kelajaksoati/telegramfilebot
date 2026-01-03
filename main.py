import asyncio
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- SOZLAMALAR ---
API_TOKEN = '8421450271:AAEYRTHjB7nNdV1oeTu42xlm7PK3YbQoG78'
CHANNEL_ID = '@ish_reja_uz'
ADMIN_ID = 1689979186

# --- VEB SERVER (24/7 UCHUN) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot @ish_reja_uz uchun faol holatda!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BOT QISMI ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Boshlang'ich matn shabloni
current_caption = (
    "📚 {file_name}\n\n"
    "#namuna\n"
    "#taqvim_mavzu_reja\n"
    "📘 EMAKTAB.UZ uchun\n"
    "taqvim mavzu reja\n\n"
    "✅️ Kanalga obuna bo‘lish: 👇👇👇\n"
    "https://t.me/ish_reja_uz"
)

class Form(StatesGroup):
    waiting_for_new_text = State()

menu_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="📝 Matnni o'zgartirish")]
], resize_keyboard=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "Xush kelibsiz! Bot @ish_reja_uz kanali uchun tayyor.\n\n"
            "Fayl yuboring, men uni chiziqchalardan tozalab kanalga joylayman.",
            reply_markup=menu_kb
        )

@dp.message(F.text == "📝 Matnni o'zgartirish")
async def change_text_start(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "Yangi shablonni yuboring.\n"
            "⚠️ Fayl nomi o'rniga {file_name} deb yozishni unutmang."
        )
        await state.set_state(Form.waiting_for_new_text)

@dp.message(Form.waiting_for_new_text)
async def save_new_text(message: types.Message, state: FSMContext):
    global current_caption
    current_caption = message.text
    await state.clear()
    await message.answer("✅ Yangi shablon saqlandi!", reply_markup=menu_kb)

@dp.message(F.document)
async def handle_document(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        # 1. Fayl nomini olish
        raw_name = message.document.file_name
        
        # 2. Fayl kengaytmasini (.docx, .pdf) olib tashlash
        name_without_ext = raw_name.rsplit('.', 1)[0]
        
        # 3. Chiziqchalarni bo'sh joyga (probel) almashtirish
        clean_name = name_without_ext.replace('_', ' ').replace('-', ' ')
        
        # 4. Matndagi {file_name} ni yangi toza nom bilan almashtirish
        final_text = current_caption.replace("{file_name}", clean_name)
        
        try:
            await bot.send_document(
                chat_id=CHANNEL_ID,
                document=message.document.file_id,
                caption=final_text
            )
            await message.reply(f"✅ Kanalga yuborildi: {clean_name}", parse_mode="Markdown")
        except Exception as e:
            await message.reply(f"❌ Xato yuz berdi: {e}")

async def main():
    keep_alive()  # Veb-serverni ishga tushirish
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if name == 'main':
    asyncio.run(main())
