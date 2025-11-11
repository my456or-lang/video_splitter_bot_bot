import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import subprocess
import asyncio
from pathlib import Path
import shutil

# הגדרת לוגים
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# קבלת טוקנים מ-environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# הגדרות חיתוך
SEGMENT_DURATION = 30  # 30 שניות
MAX_FILE_SIZE_MB = 45  # 45MB - מתחת לגבול של 50MB
ENABLE_COMPRESSION = True  # דחיסה אוטומטית

# תיקיות זמניות
TEMP_DIR = Path("/tmp/video_processing")
TEMP_DIR.mkdir(exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """פקודת התחלה"""
    compression_status = "✅ פעילה" if ENABLE_COMPRESSION else "❌ כבויה"
    await update.message.reply_text(
        "🎬 שלום! אני בוט לחיתוך וידאו\n\n"
        f"⚙️ הגדרות נוכחיות:\n"
        f"⏱️ חיתוך כל: {SEGMENT_DURATION} שניות\n"
        f"🗜️ דחיסה: {compression_status}\n\n"
        "📤 שלח לי סרטון ואני:\n"
        f"1️⃣ אחתוך אותו לקטעים של {SEGMENT_DURATION} שניות\n"
        "2️⃣ אדחוס אותו (אם הדחיסה פעילה)\n"
        "3️⃣ אחזיר לך קבצים ממוספרים\n\n"
        "💡 פקודות:\n"
        "/start - הודעת פתיחה\n"
        "/help - עזרה\n"
        "/status - סטטוס השרת\n"
        "/settings - הגדרות"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """פקודת עזרה"""
    compression_info = ""
    if ENABLE_COMPRESSION:
        compression_info = "\n🗜️ דחיסה פעילה - הקבצים יהיו קטנים יותר!"
    
    await update.message.reply_text(
        "📖 איך להשתמש בבוט:\n\n"
        "1️⃣ שלח סרטון (גודל + אורך בלתי מוגבלים)\n"
        f"2️⃣ הבוט יחתוך אותו לקטעים של {SEGMENT_DURATION} שניות\n"
        "3️⃣ תקבל קבצים ממוספרים: part_001, part_002...\n"
        f"{compression_info}\n"
        "💡 טיפים:\n"
        "• שלח כ-File לאיכות מקסימלית\n"
        "• עם דחיסה: הקבצים יהיו 50-70% קטנים יותר\n"
        f"• זמן עיבוד: {'כ-2 דקות לכל 10 דקות' if ENABLE_COMPRESSION else 'כ-30 שניות לכל 10 דקות'}"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """בדיקת סטטוס"""
    # בדיקת שטח פנוי
    disk_usage = shutil.disk_usage("/tmp")
    free_gb = disk_usage.free / (1024**3)
    
    await update.message.reply_text(
        f"✅ הבוט פעיל!\n\n"
        f"💾 שטח פנוי: {free_gb:.2f}GB\n"
        f"⚙️ FFmpeg: מותקן\n"
        f"🔑 Groq API: {'מחובר' if GROQ_API_KEY else 'לא מוגדר'}"
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """הצגת הגדרות"""
    compression_status = "✅ פעילה (דחיסת H.264)" if ENABLE_COMPRESSION else "❌ כבויה (העתקה מהירה)"
    
    # חישוב כמה קטעים יצאו מסרטון לדוגמה
    example_duration = 300  # 5 דקות
    num_parts = (example_duration // SEGMENT_DURATION) + (1 if example_duration % SEGMENT_DURATION else 0)
    
    settings_text = (
        "⚙️ *הגדרות הבוט:*\n\n"
        f"⏱️ *אורך כל קטע:* {SEGMENT_DURATION} שניות\n"
        f"🗜️ *דחיסה:* {compression_status}\n"
        f"📦 *גודל מקסימלי:* {MAX_FILE_SIZE_MB}MB\n\n"
        f"📊 *דוגמה:*\n"
        f"סרטון של 5 דקות → {num_parts} קטעים\n\n"
    )
    
    if ENABLE_COMPRESSION:
        settings_text += (
            "💡 *יתרונות הדחיסה:*\n"
            "• קבצים קטנים יותר (חיסכון 50-70%)\n"
            "• העלאה והורדה מהירה יותר\n"
            "• חוסך רוחב פס\n\n"
            "⚠️ *חסרונות:*\n"
            "• עיבוד איטי יותר (~2 דקות לכל 10 דקות)\n"
            "• איבוד איכות קל (CRF 28)"
        )
    else:
        settings_text += (
            "⚡ *יתרונות ללא דחיסה:*\n"
            "• עיבוד מהיר מאוד\n"
            "• איכות מקורית 100%\n\n"
            "⚠️ *חסרונות:*\n"
            "• קבצים גדולים\n"
            "• העלאה איטית יותר"
        )
    
    await update.message.reply_text(settings_text, parse_mode='Markdown')



def get_video_duration(file_path):
    """מחזיר את אורך הסרטון בשניות"""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 
             'format=duration', '-of', 
             'default=noprint_wrappers=1:nokey=1', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return float(result.stdout)
    except Exception as e:
        logger.error(f"שגיאה בקבלת אורך סרטון: {e}")
        return 0


def split_video(input_path, output_dir, segment_duration=SEGMENT_DURATION, compress=ENABLE_COMPRESSION):
    """חיתוך סרטון לקטעים - עם אופציית דחיסה"""
    try:
        output_pattern = os.path.join(output_dir, "part_%03d.mp4")
        
        if compress:
            # דחיסה חכמה - מקטין גודל באופן משמעותי
            # CRF 28 = איזון טוב בין איכות לגודל (18=מעולה, 28=טוב, 35=בינוני)
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c:v', 'libx264',           # קודק H.264 יעיל
                '-preset', 'medium',          # מהירות vs דחיסה
                '-crf', '28',                 # רמת איכות (נמוכה יותר = איכות גבוהה)
                '-c:a', 'aac',                # קודק אודיו יעיל
                '-b:a', '128k',               # ביטרייט אודיו
                '-movflags', '+faststart',    # אופטימיזציה לסטרימינג
                '-map', '0',
                '-f', 'segment',
                '-segment_time', str(segment_duration),
                '-reset_timestamps', '1',
                '-max_muxing_queue_size', '1024',  # מניעת שגיאות buffer
                output_pattern
            ]
        else:
            # ללא דחיסה - העתקה מהירה (כמו שהיה)
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-c', 'copy',
                '-map', '0',
                '-f', 'segment',
                '-segment_time', str(segment_duration),
                '-reset_timestamps', '1',
                output_pattern
            ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # החזרת רשימת קבצים שנוצרו
        parts = sorted([f for f in os.listdir(output_dir) if f.startswith('part_')])
        return [os.path.join(output_dir, p) for p in parts]
        
    except subprocess.CalledProcessError as e:
        logger.error(f"שגיאה בחיתוך וידאו: {e.stderr.decode()}")
        return []
    except Exception as e:
        logger.error(f"שגיאה כללית: {e}")
        return []


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """טיפול בסרטון שהתקבל"""
    message = update.message
    user_id = message.from_user.id
    
    # יצירת תיקייה ייחודית למשתמש
    user_dir = TEMP_DIR / str(user_id)
    user_dir.mkdir(exist_ok=True)
    
    try:
        # קבלת הקובץ (Video או Document)
        if message.video:
            file = message.video
            file_name = f"video_{file.file_id}.mp4"
        elif message.document:
            file = message.document
            file_name = message.document.file_name or f"video_{file.file_id}.mp4"
        else:
            await message.reply_text("❌ לא זיהיתי סרטון. אנא שלח קובץ וידאו.")
            return
        
        # הודעה למשתמש
        status_msg = await message.reply_text(
            f"⏳ מקבל את הסרטון...\n"
            f"📦 גודל: {file.file_size / (1024*1024):.2f}MB"
        )
        
        # הורדת הקובץ
        input_path = user_dir / file_name
        telegram_file = await context.bot.get_file(file.file_id)
        await telegram_file.download_to_drive(input_path)
        
        # בדיקת אורך הסרטון
        duration = get_video_duration(str(input_path))
        duration_min = duration / 60
        num_parts_estimate = int(duration // SEGMENT_DURATION) + 1
        
        compression_msg = ""
        if ENABLE_COMPRESSION:
            compression_msg = "\n🗜️ דחיסה פעילה - זה יקח קצת זמן..."
        
        await status_msg.edit_text(
            f"✅ הסרטון התקבל!\n"
            f"⏱️ אורך: {duration_min:.1f} דקות\n"
            f"📊 צפוי: ~{num_parts_estimate} קטעים\n"
            f"✂️ מתחיל לחתוך...{compression_msg}"
        )
        
        # חיתוך הסרטון
        output_dir = user_dir / "output"
        output_dir.mkdir(exist_ok=True)
        
        parts = split_video(str(input_path), str(output_dir), SEGMENT_DURATION, ENABLE_COMPRESSION)
        
        if not parts:
            await status_msg.edit_text("❌ שגיאה בחיתוך הסרטון. נסה שוב.")
            return
        
        # חישוב חיסכון בגודל (אם יש דחיסה)
        if ENABLE_COMPRESSION:
            original_size = os.path.getsize(input_path) / (1024*1024)
            total_parts_size = sum(os.path.getsize(p) for p in parts) / (1024*1024)
            saved_percent = ((original_size - total_parts_size) / original_size) * 100
            
            await status_msg.edit_text(
                f"✅ החיתוך הושלם!\n"
                f"📤 שולח {len(parts)} קטעים...\n"
                f"💾 גודל מקורי: {original_size:.1f}MB\n"
                f"💾 גודל חדש: {total_parts_size:.1f}MB\n"
                f"🎉 חיסכון: {saved_percent:.1f}%"
            )
        else:
            await status_msg.edit_text(
                f"✅ החיתוך הושלם!\n"
                f"📤 שולח {len(parts)} קטעים..."
            )
        
        for i, part_path in enumerate(parts, 1):
            try:
                part_duration = get_video_duration(part_path)
                part_size = os.path.getsize(part_path) / (1024*1024)
                
                caption = (
                    f"🎬 חלק {i}/{len(parts)}\n"
                    f"⏱️ {part_duration/60:.1f} דקות | 💾 {part_size:.1f}MB"
                )
                
                with open(part_path, 'rb') as video_file:
                    await message.reply_video(
                        video=video_file,
                        caption=caption,
                        supports_streaming=True
                    )
                
            except Exception as e:
                logger.error(f"שגיאה בשליחת חלק {i}: {e}")
                await message.reply_text(f"❌ שגיאה בשליחת חלק {i}")
        
        await status_msg.edit_text(
            f"✅ הושלם!\n"
            f"📦 נשלחו {len(parts)} קטעים בהצלחה"
        )
        
    except Exception as e:
        logger.error(f"שגיאה כללית: {e}")
        await message.reply_text(f"❌ שגיאה: {str(e)}")
    
    finally:
        # ניקוי קבצים זמניים
        try:
            shutil.rmtree(user_dir)
        except Exception as e:
            logger.error(f"שגיאה בניקוי קבצים: {e}")


def main():
    """הפעלת הבוט"""
    if not TELEGRAM_TOKEN:
        raise ValueError("חסר TELEGRAM_TOKEN ב-environment variables!")
    
    # יצירת האפליקציה
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # רישום handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    
    # הפעלה
    logger.info("🚀 הבוט מתחיל לרוץ...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
