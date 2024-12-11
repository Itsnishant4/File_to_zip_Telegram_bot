import os
import zipfile
import ssl
import certifi
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.ext import CallbackQueryHandler
import random
import asyncio
from aiohttp import web
import threading

# Bot token
TOKEN = "7919904291:AAGku102DsYoZ1dpZ9Szy3vBfYg4_OzRhO4"
random_number = random.randint(1, 1000000)
PORT = int(os.environ.get("PORT", 8080))


# Create SSL context
ssl_context = ssl.create_default_context(cafile=certifi.where())

# Maximum file size allowed (50MB)
MAX_FILE_SIZE = 52428800  # 50MB

# Global variable to track ongoing download process
downloading = False
downloading_lock = threading.Lock()

# Command: /start
async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Stop Download", callback_data="stop_download")],
        [InlineKeyboardButton("Clear All Files", callback_data="clear_all")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Hello! Send me files or a URL, and I will compress them into a ZIP file for you. "
        "Use /zip to create the ZIP file and /clearall to stop and delete previous uploads.",
        reply_markup=reply_markup
    )

# Command: clear all files
async def clear_all(update: Update, context: CallbackContext):
    query = update.callback_query  # Get the callback query
    user_id = query.from_user.id  # Get the user ID from the query
    user_temp_dir = f"temp_files_{user_id}"

    if os.path.exists(user_temp_dir) and os.listdir(user_temp_dir):  # Check if files exist
        for file_name in os.listdir(user_temp_dir):
            file_path = os.path.join(user_temp_dir, file_name)
            os.remove(file_path)
        await query.edit_message_text("All files have been cleared.")
    else:
        await query.edit_message_text("No files found to delete!")

# CallbackQuery handler
async def handle_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    action = query.data

    if action == "clear_all":
        await clear_all(update, context)
    elif action == "stop_download":
        await stop_download(update, context)  # You need to define this function as well

    # Answer the callback query to remove the "loading" animation
    await query.answer()

# Stop the download process
async def stop_download(update: Update, context: CallbackContext):
    global downloading
    if downloading:
        downloading = False
        await update.callback_query.answer("Download stopped!")
    else:
        await update.callback_query.answer("No download in progress.")



# Command: /clearall
async def clear__all(update: Update, context: CallbackContext):
    global downloading

    user_id = update.message.from_user.id
    user_temp_dir = f"temp_files_{user_id}"

    if downloading:
        downloading = False
        await update.message.reply_text("Download has been stopped. Proceeding to clear files.")

    if os.path.exists(user_temp_dir):
        for file_name in os.listdir(user_temp_dir):
            file_path = os.path.join(user_temp_dir, file_name)
            os.remove(file_path)
        await update.message.reply_text("All files have been deleted successfully. Feel free to send more!")
    else:
        await update.message.reply_text("No files found to delete!")

# Cool progress bar with emojis
def generate_progress_bar(percentage):
    completed = int(percentage // 1)  # 5% per block of progress
    remaining = 20 - completed
    progress_bar = "🟩" * completed + "⬛" * remaining
    return f"{progress_bar} {percentage:.2f}%"

# Handle files sent by the user
CHUNK_SIZE = 5 * 1024 * 1024  # 5MB per chunk

async def handle_file(update: Update, context: CallbackContext):
    global downloading

    user_id = update.message.from_user.id
    user_temp_dir = f"temp_files_{user_id}"

    if not os.path.exists(user_temp_dir):
        os.makedirs(user_temp_dir)

    file = None
    file_path = ""

    # Generate a random file name for each file
    random_file_name = f"{random.randint(1, 1000000)}"

    # Check if the message contains a document, photo, video, or audio
    if update.message.document:
        file = update.message.document
        file_path = os.path.join(user_temp_dir, f"{random_file_name}_{file.file_name}")
    elif update.message.photo:
        file = update.message.photo[-1]  # Get the largest photo
        file_path = os.path.join(user_temp_dir, f"{random_file_name}_photo.jpg")
        await update.message.reply_photo(photo=file.file_id)  # Preview the image
    elif update.message.video:
        file = update.message.video
        file_path = os.path.join(user_temp_dir, f"{random_file_name}_video.mp4")
        await update.message.reply_video(video=file.file_id)  # Preview the video
    elif update.message.audio:
        file = update.message.audio
        file_path = os.path.join(user_temp_dir, f"{random_file_name}_audio.mp3")
        await update.message.reply_audio(audio=file.file_id)  # Preview the audio
    else:
        await update.message.reply_text("Unsupported file type.")
        return

    # Check file size before attempting to download
    if file.file_size > MAX_FILE_SIZE:
        await update.message.reply_text("The file is too large! Please send a file smaller than 50MB.")
        return

    # Check if a download is already in progress
    if downloading:
        await update.message.reply_text("A download is already in progress. Please stop it with /clearall.")
        return

    # Set the downloading flag to True and start the download process
    downloading = True
    await download_file(file, file_path, update, user_temp_dir)

# Function to handle the file download
async def download_file(file, file_path, update, user_temp_dir):
    global downloading

    try:
        # Notify user that the download is starting
        progress_msg = await update.message.reply_text("Downloading... 0%")

        # Download the file asynchronously
        await handle_download(file, file_path, update, progress_msg, user_temp_dir)
    except Exception as e:
        await update.message.reply_text(f"Error while downloading the file: {e}")
    finally:
        downloading = False

# Async function for downloading
async def handle_download(file, file_path, update, progress_msg, user_temp_dir):
    total_size = file.file_size
    downloaded = 0

    with open(file_path, "wb") as f:
        file_data = await file.get_file()
        async with aiohttp.ClientSession() as session:
            async with session.get(file_data.file_path) as response:
                while downloaded < total_size:
                    chunk = await response.content.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Calculate download progress
                    progress = (downloaded / total_size) * 100
                    progress_bar = generate_progress_bar(progress)

                    # Update progress message
                    try:
                        await progress_msg.edit_text(f"Downloading... {progress_bar} /stop Downloding")
                    except Exception as e:
                        await progress_msg.edit_text(f"Error while updating progress: {e}")
                        progress_msg = None  # Set progress_msg to None to avoid further attempts

    await update.message.reply_text(f"File `{os.path.basename(file_path)}` has been downloaded! Send me more files or /zip to zip all files.")
    await progress_msg.delete()

# Command: /zip
async def zip_files(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_temp_dir = f"temp_files_{user_id}"

    if not os.path.exists(user_temp_dir) or len(os.listdir(user_temp_dir)) == 0:
        await update.message.reply_text("No files to compress! Please send some files first.")
        return

    # Notify user that the ZIP file is being created
    zip_msg = await update.message.reply_text("Creating ZIP file... This might take some time.")

    zip_file_path = os.path.join(user_temp_dir, f"files_{user_id}.zip")
    files_in_temp = os.listdir(user_temp_dir)
    total_files = len(files_in_temp)

    try:
        # Asynchronously create ZIP file
        await create_zip_file_with_progress(zip_file_path, files_in_temp, total_files, zip_msg, user_temp_dir)

        # Send the ZIP file
        await update.message.reply_document(document=open(zip_file_path, "rb"))
        await update.message.reply_text("Files have been successfully compressed and sent.")
    except Exception as e:
        await update.message.reply_text(f"Error while creating ZIP file: {e}")
    finally:
        # Clean up the ZIP file after sending
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)

        # Delete the ZIP creation message
        await zip_msg.delete()

# Function to create ZIP file with progress updates
async def create_zip_file_with_progress(zip_file_path, files_in_temp, total_files, zip_msg, user_temp_dir):
    try:
        print(f"Starting to create ZIP file: {zip_file_path}")
        
        # Ensure that the ZIP directory exists
        zip_dir = os.path.dirname(zip_file_path)
        if not os.path.exists(zip_dir):
            os.makedirs(zip_dir)
        
        with zipfile.ZipFile(zip_file_path, "w") as zipf:
            for idx, file_name in enumerate(files_in_temp):
                file_path = os.path.join(user_temp_dir, file_name)
                print(f"Adding {file_name} to the ZIP file...")

                # Add file to the ZIP
                zipf.write(file_path, arcname=file_name)

                # Calculate progress based on the number of files processed
                progress = (idx + 1) / total_files * 100
                progress_bar = generate_progress_bar(progress)

                # Update the progress message (within the Telegram bot)
                try:
                    await zip_msg.edit_text(f"Creating ZIP file... {progress_bar}")
                except Exception as e:
                    print(f"Error while updating progress: {e}")

        print("ZIP file created successfully.")
    except Exception as e:
        print(f"Error during ZIP creation: {e}")
        raise Exception(f"Error while creating ZIP file: {e}")

# Command: /joke
async def joke(update: Update, context: CallbackContext):
    jokes = ["Why don't skeletons fight each other? They don't have the guts.", 
             "I told my wife she was drawing her eyebrows too high. She looked surprised."]
    await update.message.reply_text(random.choice(jokes))

# Command: /help
async def help(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Here are the available commands:\n"
        "/start - Start the bot\n"
        "/zip - Create a ZIP file from your uploaded files\n"
        "/clearall - Clear all uploaded files\n"
        "/joke - Get a random joke\n"
        "/help - Display this help message"
    )

# Command: /url
async def download_from_url(update: Update, context: CallbackContext):
    global downloading
    if not context.args:
        await update.message.reply_text("Please provide a URL to download, e.g., /url <URL>.")
        return
    
    url = context.args[0]
    user_id = update.message.from_user.id
    user_dir = f"temp_files_{user_id}"

    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    # Extract filename from URL
    file_name = url.split("/")[-1] or "downloaded_file"
    file_path = os.path.join(user_dir, file_name)

    msg = await update.message.reply_text("Starting download...")

    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download file: HTTP {response.status}")
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded_size = 0
                downloading = True
                with open(file_path, "wb") as f:
                    while True:
                        chunk = await response.content.read(5 * 1024 * 1024)  # 1 MB chunks
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Calculate download progress
                        progress = (downloaded_size / total_size) * 100
                        progress_bar = generate_progress_bar(progress)

                        try:
                            await msg.edit_text(f"Downloading... {progress_bar} /stop Downloding")
                        except Exception as e:
                            await msg.edit_text(f"Error while updating progress: {e}")
        await msg.edit_text(f"File `{file_name}` has been downloaded! Use /zip to compress all files Or Send Me More Files.")
    except Exception as e:
        await msg.edit_text(f"Error while downloading the file from URL: {e}")
        downloading = False

# Main function
def main():
    app = Application.builder().token(TOKEN).read_timeout(120000).write_timeout(120000).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clearall", clear__all))
    app.add_handler(CommandHandler("zip", zip_files))
    app.add_handler(CommandHandler("joke", joke))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("url", download_from_url))
    app.add_handler(CommandHandler("stop", stop_download))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(MessageHandler(filters.PHOTO, handle_file))
    app.add_handler(MessageHandler(filters.VIDEO, handle_file))
    app.add_handler(MessageHandler(filters.AUDIO, handle_file))
    app.add_handler(CallbackQueryHandler(handle_buttons))

    print("Bot is running. Press Ctrl+C to stop.")
    web_app = web.Application()
    web.run_app(web_app, host="0.0.0.0", port=PORT)
    app.run_polling()


# Entry point
if __name__ == "__main__":
    main()