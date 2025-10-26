import logging
import os
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# -------------------------------
# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------
# Переменные окружения
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {int(i) for i in os.getenv("ADMIN_IDS", "123456789").split(",")}
GROUP_INVITE_LINK = os.getenv("GROUP_INVITE_LINK", "https://t.me/+your_invite_link")

if not API_TOKEN:
    logger.error("BOT_TOKEN не установлен")
    raise ValueError("BOT_TOKEN не установлен")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# -------------------------------
# В памяти храним заявки {user_id: текст заявки}
requests = {}

# -------------------------------
# /start
@dp.message(CommandStart())
async def start(message: Message):
    await message.reply("Привет! Чтобы подать заявку на вступление в группу, напиши причину:")

# -------------------------------
# Обработка текстовых сообщений (заявка)
@dp.message(F.text & ~F.bot)
async def handle_request(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    text = message.text.strip()

    if not text:
        return await message.reply("Пожалуйста, напиши причину вступления 🙂")

    # Сохраняем заявку
    requests[user_id] = text

    # Клавиатура для администратора
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}")
        ]
    ])

    msg_text = f"🔔 Новая заявка на вступление\n👤 @{username}\n💬 {text}"
    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, msg_text, reply_markup=keyboard)

    await message.reply("✅ Ваша заявка отправлена на рассмотрение администраторам.")

# -------------------------------
# Обработка inline-кнопок approve/reject
@dp.callback_query(F.data.startswith(("approve:", "reject:")))
async def process_callback(callback: CallbackQuery):
    action, user_id_str = callback.data.split(":")
    user_id = int(user_id_str)

    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("❌ У вас нет прав для этой кнопки.", show_alert=True)

    reason = requests.pop(user_id, None)
    if not reason:
        return await callback.answer("❌ Заявка уже обработана или не найдена.", show_alert=True)

    try:
        if action == "approve":
            await bot.send_message(user_id, f"✅ Ваша заявка одобрена! Вот ссылка: {GROUP_INVITE_LINK}")
            await callback.message.edit_text(f"✅ Одобрено: @{callback.from_user.username} одобрил заявку пользователя {user_id}")
        else:  # reject
            await bot.send_message(user_id, "❌ К сожалению, ваша заявка отклонена.")
            await callback.message.edit_text(f"❌ Отклонено: @{callback.from_user.username} отклонил заявку пользователя {user_id}")
        await callback.answer("✅ Действие выполнено")
    except Exception as e:
        logger.error(f"Ошибка при уведомлении пользователя {user_id}: {e}")
        await callback.answer("❌ Не удалось уведомить пользователя", show_alert=True)

# -------------------------------
# Webhook: запуск и остановка
async def on_startup(_):
    host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    webhook_url = f"https://{host}/webhook"
    try:
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
        logger.info(f"Webhook установлен: {webhook_url}")
    except Exception as e:
        logger.error(f"Ошибка при установке webhook: {e}")
        raise

async def on_shutdown(_):
    try:
        await bot.delete_webhook()
        logger.info("Webhook удалён")
    except Exception as e:
        logger.error(f"Ошибка при удалении webhook: {e}")

# -------------------------------
# Запуск aiohttp приложения
def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path='/webhook')
    setup_application(app, dp, bot=bot)
    web.run_app(app, host='0.0.0.0', port=int(os.getenv("PORT", 10000)))

if __name__ == "__main__":
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    main()
