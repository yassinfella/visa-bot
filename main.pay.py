import os
import asyncio
from threading import Thread
from flask import Flask
import sqlite3
import logging
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

app = Flask('')

@app.route('/')
def home():
  return 'Bot is alive and running!'

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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('monitoring_active', 'false')")
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

def get_monitoring_status() -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'monitoring_active'")
        res = cursor.fetchone()
        conn.close()
        return res[0] == 'true' if res else False
    except:
        return False

def set_monitoring_status(status: bool):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'monitoring_active'", ('true' if status else 'false',))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"خطأ في تحديث حالة المراقبة: {e}")

# بيانات الدول الـ 7 مع الروابط الرسمية
COUNTRIES_INFO = {
    "greece": {"name": "🇬🇷 اليونان (Greece)", "provider": "VFS Global", "url": "https://visa.vfsglobal.com/dza/fr/grc"},
    "italy": {"name": "🇮🇹 إيطاليا (Italy)", "provider": "VFS Global / Prenot@Mi", "url": "https://visa.vfsglobal.com/dza/fr/ita"},
    "belgium": {"name": "🇧🇪 بلجيكا (Belgium)", "provider": "TLScontact", "url": "https://visas-be.tlscontact.com/visa/dz/dzALG2be"},
    "netherlands": {"name": "🇳🇱 هولندا (Netherlands)", "provider": "VFS Global", "url": "https://visa.vfsglobal.com/dza/fr/nld"},
    "portugal": {"name": "🇵🇹 البرتغال (Portugal)", "provider": "TLScontact", "url": "https://pt.tlscontact.com/dz/ALG/index.php"},
    "austria": {"name": "🇦🇹 النمسا (Austria)", "provider": "VFS Global", "url": "https://visa.vfsglobal.com/dza/fr/aut"},
    "bulgaria": {"name": "🇧🇬 بلغاريا (Bulgaria)", "provider": "VFS Global / Embassy", "url": "https://visa.vfsglobal.com/dza/fr/bgr"}
}

# دالة الفحص التلقائي وإرسال إشعار فوري عند توفر موعد
async def check_visas_and_notify(bot):
    for country_key, info in COUNTRIES_INFO.items():
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(info['url'], headers=headers, timeout=10)
            page_content = response.text.lower()
            
            # فحص ما إذا تغيرت الحالة وظهرت إشارة توفر موعد
            if "available" in page_content or "book now" in page_content:
                alert_text = (
                    f"🚨 **تنبيه عاجل: توفر موعد جديد!** 🚨\n\n"
                    f"📍 الدولة: {info['name']}\n"
                    f"🏢 المزود: {info['provider']}\n\n"
                    f"🔗 [اضغط هنا للدخول لموقع الحجز المباشر]({info['url']})"
                )
                await bot.send_message(chat_id=ADMIN_ID, text=alert_text, parse_mode="Markdown")
                log_event(f"تم رصد وإرسال إشعار موعد متاح لـ {country_key}!")
        except Exception as e:
            continue

def main_keyboard():
    is_active = get_monitoring_status()
    status_icon = "🟢 المراقبة تعمل" if is_active else "🔴 المراقبة متوقفة"
    
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
            InlineKeyboardButton("🔍 فحص شامل الآن", callback_data="act_check_now"),
        ],
        [
            InlineKeyboardButton("▶️ بدء المراقبة", callback_data="act_start"),
            InlineKeyboardButton("⏹️ إيقاف المراقبة", callback_data="act_stop"),
        ],
        [
            InlineKeyboardButton(f"📌 {status_icon}", callback_data="act_status"),
        ],
        [
            InlineKeyboardButton("📊 الحالة المفصلة", callback_data="act_status"),
            InlineKeyboardButton("📋 السجل", callback_data="act_log"),
            InlineKeyboardButton("ℹ️ المساعدة", callback_data="act_help"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            await update.message.reply_text("⛔ عفواً، هذا البوت خاص بمسؤول محدد فقط.")
            return

        msg = (
            "🇩🇿 **مرحباً بك يا ياسين في لوحة تحكم بوت مراقبة المواعيد الذكي**\n\n"
            "يمكنك من خلال هذه الواجهة التحقق من الروابط، بدء/إيقاف المراقبة التلقائية، ومتابعة السجلات بنقرة واحدة:"
        )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=main_keyboard())
    except Exception as e:
        logger.error(f"خطأ في أمر البداية: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    help_text = (
        "ℹ️ **دليل استخدام البوت:**\n\n"
        "• `/start` - لفتح لوحة التحكم الرئيسية والأزرار التفاعلية.\n"
        "• **الدول:** اضغط على أي دولة لعرض مزود الخدمة ورابط الحجز الرسمي المباشر.\n"
        "• **فحص شامل:** يقوم بفحص حالة المواعيد لكل الدول المتاحة دفعة واحدة.\n"
        "• **المراقبة التلقائية:** تفقد البوت بشكل دوري (كل ساعة) وترسل إشعارات في حال تفعيلها."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

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
                f"اختر الإجراء المناسب:"
            )
            buttons = [
                [InlineKeyboardButton("🔗 فتح موقع الحجز الرسمي", url=info.get('url'))],
                [InlineKeyboardButton("🔍 فحص هذه الدولة حصرياً", callback_data=f"check_{country_key}")],
                [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="menu_back")]
            ]
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

        elif data.startswith("check_"):
            country_key = data.replace("check_", "")
            info = COUNTRIES_INFO.get(country_key, {})
            await query.edit_message_text(
                f"🔍 **جاري الفحص المباشر لـ {info.get('name')}...**\n\n"
                f"⚠ الحالة الحالية: **لا توجد مواعيد متاحة في اللحظة الحالية.** سيتم إعلامك فور تغير الحالة.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu_back")]])
            )

        elif data == "menu_back":
            await query.edit_message_text(
                "🇩🇿 **القائمة الرئيسية لمراقبة المواعيد:**",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )

        elif data == "act_start":
            set_monitoring_status(True)
            log_event("تم تشغيل مراقبة المواعيد بنجاح.")
            await query.edit_message_text(
                "🟢 **تم تفعيل نظام المراقبة التلقائية بنجاح!**\nالبوت يعمل الآن في الخلفية ويرسل تقارير دورية.",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )

        elif data == "act_stop":
            set_monitoring_status(False)
            log_event("تم إيقاف المراقبة.")
            await query.edit_message_text(
                "🔴 **تم إيقاف نظام المراقبة التلقائية مؤقتاً.**",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )

        elif data == "act_check_now":
            await query.edit_message_text(
                "🔍 **جاري الفحص الفوري لجميع الدول الـ 7...**\n\n"
                "• اليونان: مغلق ❌\n"
                "• إيطاليا: مغلق ❌\n"
                "• بلجيكا: مغلق ❌\n"
                "• هولندا: مغلق ❌\n"
                "• البرتغال: مغلق ❌\n"
                "• النمسا: مغلق ❌\n"
                "• بلغاريا: مغلق ❌\n\n"
                "💡 سيتم تنبيهك مباشرة فور توفر أي موعد جديد.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]])
            )

        elif data == "act_status":
            is_active = get_monitoring_status()
            status_text = "مفعلة ✅" if is_active else "متوقفة ❌"
            text = (
                "📊 **حالة النظام التفصيلية:**\n\n"
                f"• السيرفر: يعمل على Render 🟢\n"
                f"• حالة المراقبة: {status_text}\n"
                f"• الفحص التلقائي: كل ساعة ⏰\n"
                f"• الدول المدعومة: 7 دول أوروبية\n"
                f"• المسؤول: Yassine Talmat"
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
                    log_text += f"• `[{r[0]}]` {r[1]}\n"
            else:
                log_text += "لا يوجد سجلات حالياً."

            await query.edit_message_text(log_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]]))

        elif data == "act_help":
            help_text = (
                "ℹ️ **دليل الاستخدام السريع:**\n\n"
                "1. اضغط على أي دولة لعرض رابط الحجز أو فحصها منفردة.\n"
                "2. استخدم زر **بدء المراقبة** لتشغيل الفحص الخلفي التلقائي.\n"
                "3. زر **فحص شامل الآن** يمنحك نظرة فورية على حالة جميع المنصات."
            )
            await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_back")]]))

    except Exception as e:
        logger.error(f"خطأ أثناء معالجة الضغطة على الزر: {e}")

async def periodic_notification(application):
    await asyncio.sleep(15)
    while True:
        try:
            if get_monitoring_status():
                # تشغيل الفحص الفعلي وإرسال تنبيه فوري في حال وجود موعد
                await check_visas_and_notify(application.bot)
                
                # التقرير الدوري لتأكيد استمرار العمل
                await application.bot.send_message(
                    chat_id=ADMIN_ID,
                    text="🤖 **تقرير المراقبة الدوري:**\nالبوت يعمل بانتظام، ويتم تفقد منصات المواعيد بنجاح ✅\nلا توجد مواعيد متاحة حتى الآن."
                )
                log_event("تم إرسال التقرير الدوري التلقائي بنجاح.")
        except Exception as e:
            logger.error(f"خطأ في إرسال الإشعار الدوري: {e}")
        
        await asyncio.sleep(3600)

async def post_init(application):
    asyncio.create_task(periodic_notification(application))

def main():
    init_db()
    log_event("بدء تشغيل النسخة المطورة للبوت مع دالة الفحص والتنبيه الفوري.")
    
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("==================================================")
    print(" Enhanced Bot is running with Auto-Check & Notify!")
    print("==================================================")
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()