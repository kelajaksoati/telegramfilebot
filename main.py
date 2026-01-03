import asyncio
import sqlite3
import logging
import os
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
file_queue = []
post_interval = 0
current_chorak = "2-chorak"

# --- BAZA ---
def init_db():
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cur.execute('''CREATE TABLE IF NOT EXISTS file_links 
                   (id INTEGER PRIMARY KEY, title TEXT, link TEXT, chorak TEXT)''')
    cur.execute('INSERT OR IGNORE INTO settings (key, value) VALUES ("show_button", "on")')
    conn.commit()
    conn.close()

def get_button_status():
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('SELECT value FROM settings WHERE key = "show_button"')
    res = cur.fetchone()
    conn.close()
    return res[0] if res else "on"

def toggle_button(status):
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('UPDATE settings SET value = ? WHERE key = "show_button"', (status,))
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

def clear_db():
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM file_links')
    conn.commit()
    conn.close()

# --- SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot faol!"
def run_flask(): app.run(host='0.0.0.0', port=8080)

# --- BOT ---
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
init_db()

# --- MENYULAR ---
def get_admin_menu():
    btn_status = "Tugma: ✅" if get_button_status() == "on" else "Tugma: ❌"
    timer_text = f"Vaqt: {post_interval//60} min" if post_interval > 0 else "Vaqt: ⚡️ Tezkor"
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Katalog yaratish"), KeyboardButton(text="📅 Chorakni tanlash")],
        [KeyboardButton(text=timer_text), KeyboardButton(text=btn_status)],
        [KeyboardButton(text="⏱️ 5 min"), KeyboardButton(text="⏱️ 15 min"), KeyboardButton(text="⚡️ Tezkor")],
        [KeyboardButton(text=f"📌 Hozir: {current_chorak}"), KeyboardButton(text="🗑 Tozalash")]
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
        await message.answer("🛠 Admin panel. Barcha funksiyalar faol.", reply_markup=get_admin_menu())

# --- SOZLAMALAR ---
@dp.message(F.text == "📅 Chorakni tanlash")
async def show_choraks(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Chorakni tanlang:", reply_markup=get_chorak_menu())

@dp.message(F.text.in_(["1-chorak", "2-chorak", "3-chorak", "4-chorak"]))
async def set_chorak(message: types.Message):
    global current_chorak
    if message.from_user.id == ADMIN_ID:
        current_chorak = message.text
        await message.answer(f"✅ Rejim: {current_chorak}", reply_markup=get_admin_menu())

@dp.message(F.text.contains("min") | (F.text == "⚡️ Tezkor"))
async def set_timer(message: types.Message):
    global post_interval
    if message.from_user.id == ADMIN_ID:
        if message.text == "⚡️ Tezkor": post_interval = 0
        elif "5" in message.text: post_interval = 300
        elif "15" in message.text: post_interval = 900
        await message.answer(f"⏱️ Vaqt o'rnatildi: {message.text}", reply_markup=get_admin_menu())

@dp.message(F.text.contains("Tugma:"))
async def toggle_btn(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        current = get_button_status()
        new_status = "off" if current == "on" else "on"
        toggle_button(new_status)
        await message.answer(f"Tugma holati: {new_status}", reply_markup=get_admin_menu())

@dp.message(F.text == "⬅️ Orqaga")
async def back_to_menu(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Asosiy menyu", reply_markup=get_admin_menu())

# --- NAVBATNI QAYTA ISHLASH ---
async def process_queue():
    while True:
        if file_queue:
            data = file_queue.pop(0)
            try:
                sent = await bot.send_document(CHANNEL_ID, data['file_id'], caption=data['caption'], reply_markup=data['kb'])
                post_link = f"https://t.me/{CHANNEL_ID.replace('@', '')}/{sent.message_id}"
                save_file_link(data['title'], post_link, data['chorak'])
            except Exception as e:
                logging.error(f"Xato: {e}")
            if post_interval > 0 and file_queue:
                await asyncio.sleep(post_interval)
        await asyncio.sleep(2)

# --- FAYL HANDLER ---
@dp.message(F.document)
async def file_handler(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        ext = message.document.file_name.split('.')[-1].lower()
        emoji = "📕" if ext == "pdf" else "📘" if ext in ["doc", "docx"] else "📊"
        file_name = message.document.file_name.rsplit('.', 1)[0]
        parts = file_name.split('_')
        v_title = f"{parts[1]} {parts[0]}" if len(parts) >= 2 else file_name.replace('_', ' ')
        
        caption = f"{emoji} {v_title} {current_chorak} 2025-2026\n\n#taqvim_mavzu_reja\n✅ @ish_reja_uz"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Obuna bo'lish", url="https://t.me/ish_reja_uz")]]) if get_button_status() == "on" else None
        
        file_queue.append({'file_id': message.document.file_id, 'caption': caption, 'kb': kb, 'title': v_title, 'chorak': current_chorak})
        await message.answer(f"📥 Navbatga olindi ({current_chorak}). Navbatda: {len(file_queue)}")

@dp.message(F.text == "📝 Katalog yaratish")
async def create_catalog(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        links = get_links_by_chorak(current_chorak)
        if not links:
            await message.answer("Fayllar topilmadi!"); return
        text = f"FANLARDAN {current_chorak.upper()} ISH REJALARI 2025-2026\n\n✅ Kerakli reja ustiga bosing:\n\n"
        for title, link in links:
            text += f"📚 {title}\n"
        text += f"\n✅ @ish_reja_uz"
        await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

@dp.message(F.text == "🗑 Tozalash")
async def reset_db(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        clear_db(); await message.answer("Baza tozalandi!")

async def main():
    Thread(target=run_flask).start()
    asyncio.create_task(process_queue())
    await dp.start_polling(bot)

if name == 'main':
    asyncio.run(main())
