import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils.webhook import SimpleRequestHandler, setup_application
from aiohttp import web
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '123456789'))  # Замените на ваш Telegram ID
GROUP_INVITE_LINK = os.getenv('GROUP_INVITE_LINK', 'https://t.me/+your_invite_link')  # Ссылка на группу

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Команда /start
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.reply("Привет! Хочешь вступить в группу? Напиши причину:")

# Обработка текстовых сообщений (заявка)
@dp.message_handler()
async def handle_request(msg: types.Message):
    text = f"🔔 Заявка на вступление\n👤 @{msg.from_user.username or msg.from_user.first_name}\n💬 {msg.text}"
    await bot.send_message(ADMIN_ID, text + "\n\n/approve_" + str(msg.from_user.id) + " /reject_" + str(msg.from_user.id))

# Одобрение заявки
@dp.message_handler(lambda m: m.text.startswith('/approve_'))
async def approve(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ У вас нет прав для этой команды.")
        return
    user_id = int(msg.text.split('_')[1])
    await bot.send_message(user_id, f"✅ Ваша заявка одобрена! Вот ссылка: {GROUP_INVITE_LINK}")
    await msg.answer("Пользователь уведомлён.")

# Отклонение заявки
@dp.message_handler(lambda m: m.text.startswith('/reject_'))
async def reject(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ У вас нет прав для этой команды.")
        return
    user_id = int(msg.text.split('_')[1])
    await bot.send_message(user_id, "❌ К сожалению, ваша заявка отклонена.")
    await msg.answer("Пользователь уведомлён об отказе.")

# Webhook: запуск и остановка
async def on_startup(_):
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
    await bot.set_webhook(webhook_url)
    logger.info(f"Webhook установлен: {webhook_url}")

async def on_shutdown(_):
    await bot.delete_webhook()
    logger.info("Webhook удалён")

# Настройка aiohttp-сервера
def main():
    app = setup_application(dp, bot, on_startup=on_startup, on_shutdown=on_shutdown)
    app.add_handler(SimpleRequestHandler(bot, dp, path='/webhook'))
    web.run_app(app, host='0.0.0.0', port=int(os.getenv('PORT', 10000)))

if __name__ == "__main__":
    main()