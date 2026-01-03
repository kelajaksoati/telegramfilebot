import asyncio
import sqlite3
import logging
from threading import Thread
from flask import Flask
import requests
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# LOGGING - Xatoliklarni kuzatish
logging.basicConfig(level=logging.INFO)

# --- SOZLAMALAR ---
API_TOKEN = '8421450271:AAEYRTHjB7nNdV1oeTu42xlm7PK3YbQoG78'
CHANNEL_ID = '@ish_reja_uz'
ADMIN_ID = 1689979186
# SIZNING ANIQ REPLIT MANZILINGIZ
MY_REPL_URL = "https://telegramfilebot--kelajaksoati.repl.co"

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    cur.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cur.execute('INSERT OR IGNORE INTO settings (key, value) VALUES ("show_button", "on")')
    conn.commit()
    conn.close()

def toggle_button(status):
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('UPDATE settings SET value = ? WHERE key = "show_button"', (status,))
    conn.commit()
    conn.close()

def get_button_status():
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('SELECT value FROM settings WHERE key = "show_button"')
    res = cur.fetchone()
    conn.close()
    return res[0] if res else "on"

def add_user(user_id):
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM users')
    users = cur.fetchall()
    conn.close()
    return [u[0] for u in users]

# --- VEB SERVER VA AVTO-UYG'OTISH ---
app = Flask('')
@app.route('/')
def home(): return "Bot 100% Faol holatda!"

def run_flask(): app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run_flask).start()
    def ping():
        while True:
            try: 
                requests.get(MY_REPL_URL) 
                logging.info("Self-ping muvaffaqiyatli bajarildi.")
            except Exception as e: 
                logging.error(f"Pingda xato: {e}")
            time.sleep(600) # har 10 daqiqada
    Thread(target=ping).start()

# --- BOT ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
init_db()

current_caption = "📚 {file_name}\n\n✅ Kanalga obuna bo‘ling: 👇"

class AdminStates(StatesGroup):
    waiting_for_caption = State()
    waiting_for_broadcast = State()

# --- TUGMALAR ---
def get_admin_menu():
    btn_status = "✅ Yoqilgan" if get_button_status() == "on" else "❌ O'chirilgan"
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📝 Shablon")],
        [KeyboardButton(text=f"🔘 Tugma: {btn_status}"), KeyboardButton(text="📢 Reklama")]
    ], resize_keyboard=True)

inline_sub = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➕ Obuna bo'lish", url="https://t.me/ish_reja_uz")]
])

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    add_user(message.from_user.id)
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 Mukammal Admin Panelga xush kelibsiz!", reply_markup=get_admin_menu())
    else:
        await message.answer("Salom! Botdan foydalanish uchun kanalimizga obuna bo'ling.")

@dp.message(F.text.contains("🔘 Tugma:"))
async def change_button_setting(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        current = get_button_status()
        new_status = "off" if current == "on" else "on"
        toggle_button(new_status)
        text = "Kanalga yuboriladigan tugma o'chirildi ❌" if new_status == "off" else "Kanalga yuboriladigan tugma yoqildi ✅"
        await message.answer(text, reply_markup=get_admin_menu())

@dp.message(F.text == "📊 Statistika")
async def stats(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        users = get_all_users()
        await message.answer(f"📈 Bot statistikasi:\n\n👤 Foydalanuvchilar: {len(users)}\n📍 Kanal: {CHANNEL_ID}")

@dp.message(F.text == "📝 Shablon")
async def edit_cap(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Yangi shablonni yuboring. Fayl nomi chiqadigan joyga {file_name} deb yozing.")
        await state.set_state(AdminStates.waiting_for_caption)

@dp.message(AdminStates.waiting_for_caption)
async def save_cap(message: types.Message, state: FSMContext):
    global current_caption
    current_caption = message.text
    await state.clear()
    await message.answer("✅ Yangi shablon saqlandi!", reply_markup=get_admin_menu())

@dp.message(F.text == "📢 Reklama")
async def broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Barcha foydalanuvchilarga yuboriladigan reklama xabarini yuboring (rasm, video yoki matn):")
        await state.set_state(AdminStates.waiting_for_broadcast)

@dp.message(AdminStates.waiting_for_broadcast)
async def send_broadcast(message: types.Message, state: FSMContext):
    users = get_all_users()
    success = 0
    for u_id in users:
        try:
            await message.copy_to(chat_id=u_id)
            success += 1
            await asyncio.sleep(0.05) 
        except: pass
    await state.clear()
    await message.answer(f"🚀 Reklama {success} kishiga muvaffaqiyatli yuborildi.")

@dp.message(F.document)
async def file_handler(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        # Fayl nomini tozalash
        raw_name = message.document.file_name
        name_without_ext = raw_name.rsplit('.', 1)[0]
        clean_name = name_without_ext.replace('_', ' ').replace('-', ' ')
        
        caption = current_caption.replace("{file_name}", clean_name)
        
        # Tugma sozlamasini tekshirish
        kb = inline_sub if get_button_status() == "on" else None
        
        try:
            await bot.send_document(
                chat_id=CHANNEL_ID, 
                document=message.document.file_id, 
                caption=caption, 
                reply_markup=kb
            )
            await message.answer(f"✅ Kanalga yuborildi: {clean_name}", parse_mode="Markdown")
        except Exception as e:
            await message.answer(f"❌ Xatolik yuz berdi: {e}")

async def main():
    keep_alive()
    logging.info("Bot ishga tushdi...")
    await dp.start_polling(bot)

if name == 'main':
    asyncio.run(main())
