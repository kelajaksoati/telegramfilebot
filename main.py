import os
import sys
import subprocess

# --- AVTOMATIK O'RNATISH TIZIMI ---
def install_packages():
    packages = ['aiogram', 'flask', 'requests', 'pypdf', 'reportlab']
    for package in packages:
        try:
            import(package)
        except ImportError:
            print(f"🛠 {package} o'rnatilmoqda...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Bot ishlashidan oldin kutubxonalarni tekshiramiz
install_packages()

import asyncio
import sqlite3
import logging
import shutil
import io
from threading import Thread
from flask import Flask
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- SOZLAMALAR ---
API_TOKEN = '8421450271:AAEYRTHjB7nNdV1oeTu42xlm7PK3YbQoG78'
CHANNEL_ID = '@ish_reja_uz'
ADMIN_ID = 1689979186

# --- HOLATLAR ---
class AdminStates(StatesGroup):
    waiting_for_shablon = State()
    waiting_for_footer = State()
    waiting_for_ai_idea = State()

# --- GLOBAL O'ZGARUVCHILAR ---
file_queue = []
post_interval = 0
current_chorak = "2-chorak"
file_shablon = "📚 {sinf} {fan} {chorak}\n\n✅ @ish_reja_uz"
universal_footer = "\n\n✅ @ish_reja_uz"

# --- BAZA FUNKSIYALARI ---
def init_db():
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS file_links (id INTEGER PRIMARY KEY, title TEXT, link TEXT, chorak TEXT, message_id INTEGER)')
    conn.commit()
    conn.close()

def save_file_link(title, link, chorak, m_id):
    conn = sqlite3.connect('users.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO file_links (title, link, chorak, message_id) VALUES (?, ?, ?, ?)', (title, link, chorak, m_id))
    conn.commit()
    conn.close()

# --- WATERMARK (PDF ICHIGA YOZISH) ---
def create_watermark(input_path, output_path):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 45)
    can.setStrokeColorRGB(0.7, 0.7, 0.7) # Och kulrang
    can.setFillAlpha(0.25) # Shaffoflik
    can.saveState()
    can.translate(300, 450) # Sahifa markazi
    can.rotate(45) # 45 daraja qiyalik
    can.drawCentredString(0, 0, "@ish_reja_uz")
    can.restoreState()
    can.save()
    packet.seek(0)
    
    watermark_pdf = PdfReader(packet)
    existing_pdf = PdfReader(input_path)
    output = PdfWriter()

    for page in existing_pdf.pages:
        page.merge_page(watermark_pdf.pages[0])
        output.add_page(page)
    
    with open(output_path, "wb") as f:
        output.write(f)

# --- WEB SERVER (BOT O'CHMASLIGI UCHUN) ---
app = Flask('')
@app.route('/')
def home(): return "Bot 24/7 faol!"
def run_flask(): app.run(host='0.0.0.0', port=8080)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
init_db()

# --- ADMIN MENYU ---
def get_admin_menu():
    timer_text = f"⏱ {post_interval//60} min" if post_interval > 0 else "⚡️ Tezkor"
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Shablon"), KeyboardButton(text="🖋 Footer")],
        [KeyboardButton(text="📝 Katalog yaratish"), KeyboardButton(text="🤖 AI Reklama")],
        [KeyboardButton(text="📅 Chorakni tanlash"), KeyboardButton(text="⚡️ Tezkor")],
        [KeyboardButton(text=f"📌 {current_chorak}"), KeyboardButton(text="🗑 Tozalash")]
    ], resize_keyboard=True)

# --- NAVBAT ISHLASH MEXANIZMI ---
async def process_queue():
    while True:
        if file_queue:
            data = file_queue.pop(0)
            try:
                sent = await bot.send_document(CHANNEL_ID, data['file'], caption=data['caption'])
              link = f"https://t.me/{CHANNEL_ID[1:]}/{sent.message_id}"
                save_file_link(data['title'], link, current_chorak, sent.message_id)
            except Exception as e:
                logging.error(f"Xato: {e}")
            
            if post_interval > 0 and file_queue:
                await asyncio.sleep(post_interval)
        await asyncio.sleep(2)

# --- ASOSIY FAYL QABUL QILUVCHI ---
@dp.message(F.document)
async def handle_docs(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    orig_name = message.document.file_name
    name, ext = os.path.splitext(orig_name)
    
    # Yangi fayl nomi (Watermark nomda ham bo'ladi)
    new_name = f"{name} @ish_reja_uz{ext}"
    input_path = f"in_{orig_name}"
    output_path = f"out_{new_name}"
    
    file_info = await bot.get_file(message.document.file_id)
    await bot.download_file(file_info.file_path, input_path)

    # 📦 ZIP bo'lsa ichini ochish
    if ext.lower() == '.zip':
        await message.answer("📦 ZIP arxiv ochilmoqda...")
        extract_dir = f"temp_{name}"
        shutil.unpack_archive(input_path, extract_dir)
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                f_path = os.path.join(root, f)
                file_queue.append({
                    'file': types.FSInputFile(f_path),
                    'caption': file_shablon.format(sinf="---", fan=f, chorak=current_chorak),
                    'title': f, 'chorak': current_chorak
                })
        await message.answer(f"✅ ZIP ichidagi fayllar navbatga qo'shildi.")
    else:
        # 🛡 PDF bo'lsa sahifa ichiga muhr bosish
        if ext.lower() == '.pdf':
            create_watermark(input_path, output_path)
        else:
            # Word/Excel bo'lsa faqat nomini o'zgartirish
            os.rename(input_path, output_path)
            
        parts = name.split('_')
        v_sinf = parts[0].replace('-', ' ') if len(parts) >= 1 else ""
        v_fan = parts[1].replace('-', ' ') if len(parts) >= 2 else name
        
        file_queue.append({
            'file': types.FSInputFile(output_path, filename=new_name),
            'caption': file_shablon.format(sinf=v_sinf, fan=v_fan, chorak=current_chorak),
            'title': f"{v_fan} {v_sinf}", 'chorak': current_chorak
        })
        await message.answer(f"📥 {new_name} navbatga olindi.")

# --- QOLGAN ADMIN FUNKSIYALARI ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 Admin tizimi tayyor. Barcha kutubxonalar o'rnatilgan.", reply_markup=get_admin_menu())

@dp.message(F.text == "⚡️ Tezkor")
async def set_fast(message: types.Message):
    global post_interval
    post_interval = 0
    await message.answer("⚡️ Rejim: Tezkor yuborish")

@dp.message(F.text == "🗑 Tozalash")
async def clear_data(message: types.Message):
    conn = sqlite3.connect('users.db')
    conn.cursor().execute('DELETE FROM file_links')
    conn.commit()
    await message.answer("🗑 Katalog bazasi tozalandi!")

# --- ISHGA TUSHIRISH ---
async def main():
    Thread(target=run_flask).start()
    asyncio.create_task(process_queue())
    await dp.start_polling(bot)

if name == 'main':
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Botda xatolik: {e}")
