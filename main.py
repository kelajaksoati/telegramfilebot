import os, sys, subprocess, asyncio, sqlite3, logging, shutil, io
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

# 1. 🛠 AVTOMATIK O'RNATUVCHI (Xatolarni oldini oladi)
def install_packages():
    reqs = ['aiogram', 'flask', 'requests', 'pypdf', 'reportlab']
    for r in reqs:
        try:
            import(r)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", r])

if name == "main":
    if not os.path.exists(".installed"):
        install_packages()
        with open(".installed", "w") as f: f.write("done")

# 2. ⚙️ SOZLAMALAR
import os
API_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
CHANNEL_ID = '@ish_reja_uz'
ADMIN_ID = 1689979186

class AdminStates(StatesGroup):
    waiting_for_shablon = State()
    waiting_for_ai_idea = State()

file_queue = []
post_interval = 0
current_chorak = "2-chorak"
file_shablon = "📚 {sinf} {fan} {chorak}\n\n✅ @ish_reja_uz"

# 3. 🗄 BAZA VA SERVER
def init_db():
    conn = sqlite3.connect('users.db')
    conn.cursor().execute('CREATE TABLE IF NOT EXISTS file_links (id INTEGER PRIMARY KEY, title TEXT, link TEXT, chorak TEXT, message_id INTEGER)')
    conn.commit()
    conn.close()

init_db()
app = Flask('')
@app.route('/')
def home(): return "Bot 24/7 faol!"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# 4. 🎨 WATERMARK (PDF uchun)
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
    with open(output_path, "wb") as f: output.write(f)

# 5. ⌨️ MENYULAR
def get_admin_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Shablon"), KeyboardButton(text="🤖 AI Reklama")],
        [KeyboardButton(text="📝 Katalog yaratish"), KeyboardButton(text="⚡️ Tezkor")],
        [KeyboardButton(text=f"📌 {current_chorak}"), KeyboardButton(text="🗑 Tozalash")]
    ], resize_keyboard=True)

# 6. 🚀 NAVBAT TIZIMI
async def process_queue():
    while True:
        if file_queue:
            data = file_queue.pop(0)
            try:
                sent = await bot.send_document(CHANNEL_ID, data['file'], caption=data['caption'])
                conn = sqlite3.connect('users.db')
                conn.cursor().execute('INSERT INTO file_links (title, link, chorak, message_id) VALUES (?, ?, ?, ?)', 
                                    (data['title'], f"https://t.me/{CHANNEL_ID[1:]}/{sent.message_id}", current_chorak, sent.message_id))
                conn.commit()
                conn.close()
            except Exception as e: print(f"Xato: {e}")
            if post_interval > 0: await asyncio.sleep(post_interval)
        await asyncio.sleep(2)

# 7. 📥 FAYLLARNI QABUL QILISH
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
        'caption': file_shablon.format(sinf="--", fan=name, chorak=current_chorak),
        'title': name
    })
    await message.answer(f"📥 {new_name} navbatga olindi.")

# 8. 🎮 ADMIN BUYRUQLARI
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🛠 Birlashtirilgan tizim tayyor!", reply_markup=get_admin_menu())

@dp.message(F.text == "⚡️ Tezkor")
async def set_fast(message: types.Message):
    global post_interval
    post_interval = 0
    await message.answer("⚡️ Rejim: Tezkor yuborish")

@dp.message(F.text == "🗑 Tozalash")
async def clear_db(message: types.Message):
    conn = sqlite3.connect('users.db')
    conn.cursor().execute('DELETE FROM file_links')
    conn.commit()
    conn.close()
    await message.answer("🗑 Katalog tozalandi!")

# 9. 🏁 ISHGA TUSHIRISH
async def main_loop():
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    asyncio.create_task(process_queue())
    await dp.start_polling(bot)

if name == 'main':
    asyncio.run(main_loop())
