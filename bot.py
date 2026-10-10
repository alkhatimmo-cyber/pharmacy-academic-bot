import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

FOLDERS = {
    "pharmacology": "💊 علم الأدوية",
    "pharmaceutics": "🧪 الصيدلانيات",
    "medicinal": "⚗️ الكيمياء الصيدلانية",
    "clinical": "🏥 الصيدلة السريرية",
    "notes": "📚 المحاضرات والمذكرات",
}
LEVELS = {
    "level1": "المستوى الأول",
    "level2": "المستوى الثاني",
    "level3": "المستوى الثالث",
    "level4": "المستوى الرابع",
    "level5": "المستوى الخامس",
}

LEVEL5_FOLDERS = {
    "clinical_pharmacy": "Clinical Pharmacy",
    "veterinary": "Veterinary",
    "phytochemistry": "Phytochemistry",
    "intervention": "Intervention",
    "research_methodology": "Research Methodology",
    "medicinal_chemistry": "Medicinal Chemistry",
    "microbiology": "Microbiology",
    "toxicology": "Toxicology",
}

def subjects_for(level):
    return LEVEL5_FOLDERS if level == "level5" else FOLDERS


def is_admin(update):
    user = update.effective_user
    return bool(ADMIN_ID and user and str(user.id) == ADMIN_ID)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("المستوى الأول", callback_data="level_level1")],
        [InlineKeyboardButton("المستوى الثاني", callback_data="level_level2")],
        [InlineKeyboardButton("المستوى الثالث", callback_data="level_level3")],
        [InlineKeyboardButton("المستوى الرابع", callback_data="level_level4")],
        [InlineKeyboardButton("المستوى الخامس", callback_data="level_level5")],
    ]
    await update.message.reply_text(
        "🎓 مرحباً بك في Department of Academic Affairs\n\nاختر المستوى الدراسي:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def browse_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level = query.data.removeprefix("level_")
    if level not in LEVELS:
        return
    context.user_data["browse_level"] = level
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"subject_{key}")]
        for key, name in subjects_for(level).items()
    ]
    keyboard.append([InlineKeyboardButton("⬅️ اختيار مستوى آخر", callback_data="back_levels")])
    await query.message.reply_text(
        f"📚 {LEVELS[level]}\nاختر المادة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def back_levels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"level_{key}")]
        for key, name in LEVELS.items()
    ]
    await query.message.reply_text("🎓 اختر المستوى الدراسي:", reply_markup=InlineKeyboardMarkup(keyboard))

async def choose_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject = query.data.removeprefix("subject_")
    level = context.user_data.get("browse_level")
    if subject not in subjects_for(level) or level not in LEVELS:
        await query.message.reply_text("ابدأ من جديد باستخدام /start")
        return

    folder = Path("library") / level / subject
    # إظهار الملفات القديمة ضمن المستوى الرابع من دون نقلها أو حذفها
    if level == "level4" and subject in ("notes", "pharmacology"):
        legacy = Path("library") / subject
        if legacy.exists():
            folder.mkdir(parents=True, exist_ok=True)
            for f in legacy.iterdir():
                if f.is_file() and not (folder / f.name).exists():
                    import shutil
                    shutil.copy2(f, folder / f.name)

    files = sorted(f for f in folder.iterdir() if f.is_file()) if folder.exists() else []
    if not files:
        await query.message.reply_text(
            f"📂 {LEVELS[level]} — {subjects_for(level)[subject]}\nلا توجد ملفات في هذه المادة حالياً."
        )
        return
    await query.message.reply_text(f"📂 ملفات {LEVELS[level]} — {subjects_for(level)[subject]}:")
    for file in files:
        try:
            with file.open("rb") as document:
                await query.message.reply_document(document=document, filename=file.name)
        except Exception:
            logging.exception("تعذر إرسال الملف: %s", file.name)

async def upload_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("عذراً، هذا الأمر مخصص للمسؤول فقط.")
        return
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"uploadlevel_{key}")]
        for key, name in LEVELS.items()
    ]
    await update.message.reply_text("اختر المستوى الذي تريد رفع الملفات إليه:", reply_markup=InlineKeyboardMarkup(keyboard))

async def choose_upload_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update):
        await query.message.reply_text("هذا الخيار للمسؤول فقط.")
        return
    level = query.data.removeprefix("uploadlevel_")
    if level not in LEVELS:
        return
    context.user_data["upload_level"] = level
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"uploadsubject_{key}")]
        for key, name in subjects_for(level).items()
    ]
    await query.message.reply_text(f"اختر المادة في {LEVELS[level]}:", reply_markup=InlineKeyboardMarkup(keyboard))

async def choose_upload_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update):
        await query.message.reply_text("هذا الخيار للمسؤول فقط.")
        return
    subject = query.data.removeprefix("uploadsubject_")
    level = context.user_data.get("upload_level")
    if level not in LEVELS or subject not in subjects_for(level):
        return
    context.user_data["upload_subject"] = subject
    await query.message.reply_text(
        f"أرسل الآن الملف أو الصورة إلى {LEVELS[context.user_data['upload_level']]} — {subjects_for(context.user_data['upload_level'])[subject]}."
    )

async def save_in_selected_folder(update, context, source, filename):
    level = context.user_data.get("upload_level")
    subject = context.user_data.get("upload_subject")
    if level not in LEVELS or subject not in subjects_for(level):
        await update.message.reply_text("اختر المستوى والمادة أولاً باستخدام /upload")
        return
    folder = Path("library") / level / subject
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / Path(filename).name
    await source.download_to_drive(custom_path=str(destination))
    await update.message.reply_text(f"✅ تم حفظ الملف في {LEVELS[level]} — {subjects_for(level)[subject]}.")

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update) or not update.message or not update.message.document:
        return
    doc = update.message.document
    await save_in_selected_folder(update, context, await doc.get_file(), doc.file_name or "document")

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update) or not update.message or not update.message.photo:
        return
    photo = update.message.photo[-1]
    await save_in_selected_folder(update, context, await photo.get_file(), f"photo_{photo.file_unique_id}.jpg")

def main():
    if not TOKEN:
        raise RuntimeError("لم يتم العثور على BOT_TOKEN داخل ملف .env")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upload", upload_help))
    app.add_handler(CallbackQueryHandler(browse_level, pattern=r"^level_"))
    app.add_handler(CallbackQueryHandler(back_levels, pattern=r"^back_levels$"))
    app.add_handler(CallbackQueryHandler(choose_subject, pattern=r"^subject_"))
    app.add_handler(CallbackQueryHandler(choose_upload_level, pattern=r"^uploadlevel_"))
    app.add_handler(CallbackQueryHandler(choose_upload_subject, pattern=r"^uploadsubject_"))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, receive_file))
    print("البوت يعمل الآن. أوقفه باستخدام Ctrl+C.")
    app.run_polling()

if __name__ == "__main__":
    main()
