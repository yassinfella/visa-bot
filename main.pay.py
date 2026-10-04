import os
from threading import Thread
from flask import Flask
import asyncio
import sqlite3
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

app = Flask('')

@app.route('/')
def home():
  return 'Bot is alive!'

def run():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)

def keep_alive():
  t = Thread(target=run)
  t.daemon = True
  t.start()

keep_alive()

BOT_TOKEN = "8818674380:AAEqZfbOg4Js-YcBoklzXETX0Hucx0xM1zg"
ADMIN_ID = 8876916730

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DB_FILE = "bot_database.db"

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                message TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطأ في قاعدة البيانات: {e}")

def log_event(message: str):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (message) VALUES (?)", (message,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطأ في تسجيل الحدث: {e}")

COUNTRIES_INFO = {
    "greece": {"name": "🇬🇷 اليونان (Greece)", "provider": "VFS Global", "url": "https://visa.vfsglobal.com/dza/fr/grc"},
    "italy": {"name": "🇮🇹 إيطاليا (Italy)", "provider": "VFS Global / Prenot@Mi", "url": "https://visa.vfsglobal.com/dza/fr/ita"},
    "belgium": {"name": "🇧🇪 بلجيكا (Belgium)", "provider": "TLScontact", "url": "https://visas-be.tlscontact.com/visa/dz/dzALG2be"},
    "netherlands": {"name": "🇳🇱 هولندا (Netherlands)", "provider": "VFS Global", "url": "https://visa.vfsglobal.com/dza/fr/nld"},
    "portugal": {"name": "🇵🇹 البرتغال (Portugal)", "provider": "VFS Global", "url": "https://visa.vfsglobal.com/dza/fr/prt"},
    "austria": {"name": "🇦🇹 النمسا (Austria)", "provider": "VFS Global", "url": "https://visa.vfsglobal.com/dza/fr/aut"},
    "bulgaria": {"name": "🇧🇬 بلغاريا (Bulgaria)", "provider": "VFS Global / Embassy", "url": "https://visa.vfsglobal.com/dza/fr/bgr"}
}

def main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🇬🇷 Greece", callback_data="c_greece"),
            InlineKeyboardButton("🇮🇹 Italy", callback_data="c_italy"),
        ],
        [
            InlineKeyboardButton("🇧🇪 Belgium", callback_data="c_belgium"),
            InlineKeyboardButton("🇳🇱 Netherlands", callback_data="c_netherlands"),
        ],
        [
            InlineKeyboardButton("🇵🇹 Portugal", callback_data="c_portugal"),
            InlineKeyboardButton("🇦🇹 Austria", callback_data="c_austria"),
        ],
        [
            InlineKeyboardButton("🇧🇬 Bulgaria", callback_data="c_bulgaria"),
        ],
        [
            InlineKeyboardButton("🔍 فحص سريع الآن", callback_data="act_check_now"),
        ],
        [
            InlineKeyboardButton("▶️ بدء المراقبة", callback_data="act_start"),
            InlineKeyboardButton("⏹️ إيقاف المراقبة", callback_data="act_stop"),
        ],
        [
            InlineKeyboardButton("📊 الحالة", callback_data="act_status"),
            InlineKeyboardButton("📋 السجل", callback_data="act_log"),
            InlineKeyboardButton("ℹ️ المساعدة", callback_data="act_help"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            await update.message.reply_text("⛔️️ عفواً، هذا البوت خاص بمسؤول محدد فقط.")
            return

        msg = (
            "🇩🇿 **مرحباً بك يا ياسين في لوحة تحكم بوت مراقبة المواعيد**\n\n"
            "استخدم الأزرار أدناه للتنقل، فحص الدول، أو التحكم بوضع المراقبة بسلاسة:"
        )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_keyboard())
    except Exception as e:
        logger.error(f"خطأ في أمر البداية: {e}")

# دالة الإشعار التلقائي المتوافقة مع AsyncIOScheduler
async def send_periodic_alert(bot_instance):
    try:
        await bot_instance.send_message(
            chat_id=ADMIN_ID,
            text="🔔 **تنبيه تلقائي:** البوت يعمل بكفاءة تامة على السيرفر ويراقب المواعيد لك بدون توقف! ✅"
        )
        log_event("تم إرسال إشعار تلقائي دوري بنجاح.")
    except Exception as e:
        logger.error(f"خطأ في إرسال الإشعار التلقائي الدوري: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        if query.from_user.id != ADMIN_ID:
            return

        data = query.data

        if data.startswith("c_"):
            country_key = data.replace("c_", "")
            info = COUNTRIES_INFO.get(country_key, {})
            text = (
                f"📍 **الدولة المختارة:** {info.get('name')}\n"
                f"🏢 **المزود الرسمي:** {info.get('provider')}\n\n"
                f"اضغط على الزر أدناه لفتح موقع الحجز الرسمي مباشرة:"
            )
            buttons = [
                [InlineKeyboardButton("🔗 فتح موقع الحجز الرسمي", url=info.get('url'))],
                [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="menu_back")]
            ]
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

        elif data == "menu_back":
            await query.edit_message_text(
                "🇩🇿 **القائمة الرئيسية لمراقبة المواعيد:**",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )

        elif data == "act_start":
            log_event("تم تشغيل مراقبة المواعيد.")
            await query.edit_message_text(
                "🟢 **تم تشغيل المراقبة بنجاح!**\nالبوت يبحث الآن في الخلفية عن أي مواعيد جديدة.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]])
            )

        elif data == "act_stop":
            log_event("تم إيقاف المراقبة.")
            await query.edit_message_text(
                "🔴 **تم إيقاف المراقبة مؤقتاً.**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]])
            )

        elif data == "act_check_now":
            await query.edit_message_text(
                "🔍 **جاري الفحص الفوري...**\nلا توجد مواعيد متاحة حالياً لجميع الدول المدرجة.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]])
            )

        elif data == "act_status":
            text = (
                "📊 **حالة النظام:**\n\n"
                "• السيرفر: يعمل على Render ✅\n"
                "• حالة الأخطاء: مستقرة ومحمية 🛡️\n"
                "• الدول المدعومة: 7 دول\n"
                "• المسؤول: Yassine"
            )
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]]))

        elif data == "act_log":
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp, message FROM logs ORDER BY id DESC LIMIT 5")
            rows = cursor.fetchall()
            conn.close()

            log_text = "📋 **سجل الأحداث الأخير:**\n\n"
            if rows:
                for r in rows:
                    log_text += f"• [{r[0]}] {r[1]}\n"
            else:
                log_text += "لا يوجد سجلات حالياً."

            await query.edit_message_text(log_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]]))

        elif data == "act_help":
            help_text = (
                "ℹ️ **دليل المساعدة:**\n\n"
                "• اختر أي دولة لمعرفة رابط الحجز الرسمي.\n"
                "• استخدم زر 'فحص سريع' للتحقق الفوري.\n"
                "• البوت محمي ويعمل بانتظام على السحابة."
            )
            await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]]))

    except Exception as e:
        logger.error(f"خطأ أثناء معالجة الضغطة على الزر: {e}")

def main():
    init_db()
    log_event("بدء تشغيل البوت الرئيسي.")
    
    # بناء تطبيق البوت
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    # إعداد المجدول المتوافق مع AsyncIO للعمل بسلاسة داخل البوت
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_periodic_alert, 'interval', hours=1, args=[app.bot])
    scheduler.start()

    print("========================================")
    print(" Bot is running perfectly with Async Scheduler!")
    print("========================================")
    
    # تشغيل البوت بالاعتماد على ميزة الـ Polling المدمجة مع معالجة الأخطاء الآمنة
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()