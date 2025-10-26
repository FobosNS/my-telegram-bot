import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, RegexpCommandsFilter
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Настройка логирования для диагностики
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота с переменными окружения
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '123456789'))  # Ваш Telegram ID
GROUP_INVITE_LINK = os.getenv('GROUP_INVITE_LINK', 'https://t.me/+your_invite_link')

# Проверка переменных окружения
if not API_TOKEN:
    logger.error("BOT_TOKEN не установлен в переменных окружения")
    raise ValueError("BOT_TOKEN не установлен")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Обработчик команды /start
@dp.message(CommandStart())
async def start(message: Message):
    await message.reply("Привет! Хочешь вступить в группу? Напиши причину:")

# Обработка текстовых сообщений (заявка на вступление)
@dp.message()
async def handle_request(message: Message):
    username = message.from_user.username or message.from_user.first_name
    text = f"🔔 Заявка на вступление\n👤 @{username}\n💬 {message.text}"
    await bot.send_message(ADMIN_ID, text + f"\n\n/approve_{message.from_user.id} /reject_{message.from_user.id}")

# Одобрение заявки
@dp.message(RegexpCommandsFilter(regexp_commands=[r'approve_([0-9]+)']))
async def approve(message: Message, regexp_command):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    user_id = int(regexp_command.group(1))
    try:
        await bot.send_message(user_id, f"✅ Ваша заявка одобрена! Вот ссылка: {GROUP_INVITE_LINK}")
        await message.answer("Пользователь уведомлён.")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
        await message.answer("❌ Ошибка при отправке сообщения пользователю.")

# Отклонение заявки
@dp.message(RegexpCommandsFilter(regexp_commands=[r'reject_([0-9]+)']))
async def reject(message: Message, regexp_command):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    user_id = int(regexp_command.group(1))
    try:
        await bot.send_message(user_id, "❌ К сожалению, ваша заявка отклонена.")
        await message.answer("Пользователь уведомлён об отказе.")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
        await message.answer("❌ Ошибка при отправке сообщения пользователю.")

# Webhook: запуск и остановка
async def on_startup(_):
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
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

def main():
    try:
        app = web.Application()
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path='/webhook')
        setup_application(app, dp, bot=bot)
        web.run_app(app, host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {e}")
        raise

if __name__ == "__main__":
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    main()
