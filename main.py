import asyncio
import sqlite3
import logging
from threading import Thread
from flask import Flask
import requests
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- SOZLAMALAR ---
API_TOKEN = '8421450271:AAEYRTHjB7nNdV1oeTu42xlm7PK3YbQoG78'
CHANNEL_ID = '@ish_reja_uz'
ADMIN_ID = 1689979186
MY_REPL_URL = "https://telegramfilebot--kelajaksoati.repl.co"

# --- GLOBAL HOLAT ---
current_chorak = "2-chorak"

# --- BAZA ---
def init_db():
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS file_links 
                   (id INTEGER PRIMARY KEY, title TEXT, link TEXT, chorak TEXT)''')
    conn.commit()
    conn.close()

def save_file_link(title, link, chorak):
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO file_links (title, link, chorak) VALUES (?, ?, ?)', (title, link, chorak))
    conn.commit()
    conn.close()

def get_links_by_chorak(chorak):
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('SELECT title, link FROM file_links WHERE chorak = ? ORDER BY title ASC', (chorak,))
    data = cur.fetchall()
    conn.close()
    return data

# --- SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot faol!"

def run_flask(): app.run(host='0.0.0.0', port=8080)

# --- BOT ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
init_db()

# --- KLAVIATURALAR ---
def get_admin_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Katalog yaratish")],
        [KeyboardButton(text="📅 Chorakni tanlash"), KeyboardButton(text="🗑 Tozalash")],
        [KeyboardButton(text=f"📌 Hozirgi: {current_chorak}")]
    ], resize_keyboard=True)

def get_chorak_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="1-chorak"), KeyboardButton(text="2-chorak")],
        [KeyboardButton(text="3-chorak"), KeyboardButton(text="4-chorak")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ], resize_keyboard=True)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"🛠 Admin panelga xush kelibsiz.\nTanlangan chorak: {current_chorak}", reply_markup=get_admin_menu())

# --- CHORAKNI TANLASH TIZIMI ---
@dp.message(F.text == "📅 Chorakni tanlash")
async def show_choraks(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Qaysi chorak rejalari bilan ishlaymiz?", reply_markup=get_chorak_menu())

@dp.message(F.text.in_(["1-chorak", "2-chorak", "3-chorak", "4-chorak"]))
async def set_chorak(message: types.Message):
    global current_chorak
    if message.from_user.id == ADMIN_ID:
        current_chorak = message.text
        await message.answer(f"✅ Rejim o'rnatildi: {current_chorak}", reply_markup=get_admin_menu())

@dp.message(F.text == "⬅️ Orqaga")
async def back_to_menu(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Asosiy menyu", reply_markup=get_admin_menu())

# --- KATALOG YARATISH ---
@dp.message(F.text == "📝 Katalog yaratish")
async def create_catalog(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        links = get_links_by_chorak(current_chorak)
        if not links:
            await message.answer(f"Bazada {current_chorak} uchun fayllar yo'q!")
            return
        
        text = f"FANLARDAN {current_chorak.upper()} EMAKTAB.UZ TIZIMIGA YUKLASH UCHUN OʻZBEK MAKTABLARGA 2025-2026 OʻQUV YILI ISH REJALARI\n\n"
        text += "✅Oʻzingizga kerakli boʻlgan reja ustiga bosing va yuklab oling.\n\n"
        
        for title, link in links:
            text += f"📚 {title}\n"
        
        text += f"\n❗️OʻQITUVCHILARGA JOʻNATISHNI UNUTMANG❗️\n\n#taqvim_mavzu_reja\n✅ @ish_reja_uz"
        
        await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

@dp.message(F.document)
async def file_handler(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        ext = message.document.file_name.split('.')[-1].lower()
        emoji = "📕" if ext == "pdf" else "📘" if ext in ["doc", "docx"] else "📊"
        
        file_name = message.document.file_name.rsplit('.', 1)[0]
        parts = file_name.split('_')
        
        v_title = f"{parts[1]} {parts[0]}" if len(parts) >= 2 else file_name.replace('_', ' ')
        caption = f"{emoji} {v_title} {current_chorak} 2025-2026\n\n#taqvim_mavzu_reja\n✅ @ish_reja_uz"
        
        try:
            sent_msg = await bot.send_document(CHANNEL_ID, message.document.file_id, caption=caption)
            post_link = f"https://t.me/{CHANNEL_ID.replace('@', '')}/{sent_msg.message_id}"
            save_file_link(v_title, post_link, current_chorak)
            await message.answer(f"✅ {current_chorak} uchun yuborildi: {v_title}")
        except Exception as e:
            await message.answer(f"❌ Xato: {e}")

async def main():
    Thread(target=run_flask).start()
    await dp.start_polling(bot)

if name == 'main':
    asyncio.run(main())
