import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Regexp
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '123456789'))  # Ваш Telegram ID
GROUP_INVITE_LINK = os.getenv('GROUP_INVITE_LINK', 'https://t.me/+your_invite_link')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Команда /start
@dp.message(CommandStart())
async def start(message: Message):
    await message.reply("Привет! Хочешь вступить в группу? Напиши причину:")

# Обработка текстовых сообщений (заявка)
@dp.message()
async def handle_request(message: Message):
    text = f"🔔 Заявка на вступление\n👤 @{message.from_user.username or message.from_user.first_name}\n💬 {message.text}"
    await bot.send_message(ADMIN_ID, text + "\n\n/approve_" + str(message.from_user.id) + " /reject_" + str(message.from_user.id))

# Одобрение заявки
@dp.message(Regexp(r'^/approve_([0-9]+)$'))
async def approve(message: Message, regexp: Regexp):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    user_id = int(regexp.group(1))
    await bot.send_message(user_id, f"✅ Ваша заявка одобрена! Вот ссылка: {GROUP_INVITE_LINK}")
    await message.answer("Пользователь уведомлён.")

# Отклонение заявки
@dp.message(Regexp(r'^/reject_([0-9]+)$'))
async def reject(message: Message, regexp: Regexp):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    user_id = int(regexp.group(1))
    await bot.send_message(user_id, "❌ К сожалению, ваша заявка отклонена.")
    await message.answer("Пользователь уведомлён об отказе.")

# Webhook: запуск и остановка
async def on_startup(_):
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    logger.info(f"Webhook установлен: {webhook_url}")

async def on_shutdown(_):
    await bot.delete_webhook()
    logger.info("Webhook удалён")

def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path='/webhook')
    setup_application(app, dp, bot=bot)
    web.run_app(app, host='0.0.0.0', port=int(os.getenv('PORT', 10000)))

if __name__ == "__main__":
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    main()
