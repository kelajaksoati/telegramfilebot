import os
import sys
import subprocess
import asyncio
import sqlite3
import io
from threading import Thread
from flask import Flask
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# 1. 🛡 XAVFSIZ TOKENNI OLISH (Replit ogohlantirmasligi uchun)
# Bu yerda token yozilmaydi, u Secrets bo'limidan olinadi
API_TOKEN = os.environ.get('API_TOKEN')

# 2. ⚙️ SOZLAMALAR
CHANNEL_ID = '@ish_reja_uz'
ADMIN_ID = 1689979186
current_chorak = "2-chorak"
file_queue = []

# 3. 🌐 WEB SERVER (BOT O'CHMASLIGI UCHUN)
app = Flask('')
@app.route('/')
def home(): return "Bot 24/7 faol!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# 4. 🗄 BAZA VA BOT OBYEKTLARI
def init_db():
    conn = sqlite3.connect('users.db')
    conn.cursor().execute('CREATE TABLE IF NOT EXISTS file_links (id INTEGER PRIMARY KEY, title TEXT, link TEXT, chorak TEXT, message_id INTEGER)')
    conn.commit()
    conn.close()

init_db()
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# 5. 🎨 PDF WATERMARK FUNKSIYASI
def create_watermark(input_path, output_path):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 45)
    can.setStrokeColorRGB(0.7, 0.7, 0.7)
    can.setFillAlpha(0.2)
    can.saveState()
    can.translate(300, 450)
    can.rotate(45)
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

# 6. ⌨️ ADMIN MENYU
def get_admin_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Shablon"), KeyboardButton(text="🤖 AI Reklama")],
        [KeyboardButton(text="📝 Katalog yaratish"), KeyboardButton(text="⚡️ Tezkor")],
        [KeyboardButton(text=f"📌 {current_chorak}"), KeyboardButton(text="🗑 Tozalash")]
    ], resize_keyboard=True)

# 7. 🚀 NAVBAT BILAN YUBORISH
async def process_queue():
    while True:
        if file_queue:
            data = file_queue.pop(0)
            try:
                sent = await bot.send_document(CHANNEL_ID, data['file'], caption=data['caption'])
                print(f"✅ Fayl yuborildi: {data['title']}")
            except Exception as e:
                print(f"❌ Xato: {e}")
        await asyncio.sleep(3)

# 8. 📥 FAYLLARNI QAYTA ISHLASH
@dp.message(F.document)
async def handle_docs(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    orig_name = message.document.file_name
    name, ext = os.path.splitext(orig_name)
    new_name = f"{name} @ish_reja_uz{ext}"
    input_path = f"in_{orig_name}"
    output_path = f"out_{new_name}"
    
    file_info = await bot.get_file(message.document.file_id)
    await bot.download_file(file_info.file_path, input_path)

    if ext.lower() == '.pdf':
        create_watermark(input_path, output_path)
    else:
        os.rename(input_path, output_path)
        
    file_queue.append({
        'file': types.FSInputFile(output_path, filename=new_name),
        'caption': f"📚 {name} | {current_chorak}\n\n✅ @ish_reja_uz",
        'title': name
    })
    await message.answer(f"📥 {new_name} navbatga qo'shildi.")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🚀 Bot ishga tushdi. Token xavfsiz joyda.", reply_markup=get_admin_menu())

# 9. 🏁 ASOSIY ISHGA TUSHIRUVCHI
async def main():
    Thread(target=run_flask).start()
    asyncio.create_task(process_queue())
    await dp.start_polling(bot)

if name == 'main':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
