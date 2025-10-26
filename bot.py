import logging
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, and_f
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Настройка логирования для диагностики
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = {int(i) for i in os.getenv("ADMIN_IDS", "123456789").split(",")}
GROUP_INVITE_LINK = os.getenv("GROUP_INVITE_LINK", "https://t.me/+your_invite_link")
HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME")

# Проверка переменных окружения
if not API_TOKEN:
    logger.error("BOT_TOKEN не установлен")
    raise ValueError("BOT_TOKEN не установлен")
if not HOST:
    logger.error("RENDER_EXTERNAL_HOSTNAME не установлен")
    raise ValueError("RENDER_EXTERNAL_HOSTNAME не установлен")

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# В памяти храним заявки {user_id: текст заявки}
requests = {}

# Обработчик команды /start
@dp.message(CommandStart())
async def start(message: Message):
    await message.reply("Привет! Чтобы подать заявку на вступление в группу, напиши причину:")

# Обработка текстовых сообщений (заявка)
@dp.message(and_f(lambda m: m.text, lambda m: not m.from_user.is_bot))
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
        try:
            # Проверяем, может ли бот отправить сообщение админу
            await bot.send_chat_action(admin_id, "typing")
            await bot.send_message(admin_id, msg_text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка при отправке заявки админу {admin_id}: {e}")
            if "chat not found" in str(e).lower():
                logger.warning(f"Админ {admin_id} не инициировал чат с ботом. Попросите админа написать /start боту.")

    await message.reply("✅ Ваша заявка отправлена на рассмотрение администраторам.")

# Обработка inline-кнопок approve/reject
@dp.callback_query(lambda c: c.data.startswith(("approve:", "reject:")))
async def process_callback(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("❌ У вас нет прав для этой кнопки.", show_alert=True)

    action, user_id_str = callback.data.split(":")
    user_id = int(user_id_str)

    reason = requests.pop(user_id, None)
    if not reason:
        return await callback.answer("❌ Заявка уже обработана или не найдена.", show_alert=True)

    try:
        if action == "approve":
            await bot.send_message(user_id, f"✅ Ваша заявка одобрена! Вот ссылка: {GROUP_INVITE_LINK}")
            await callback.message.edit_text(
                f"✅ Одобрено: @{callback.from_user.username or callback.from_user.first_name} "
                f"одобрил заявку пользователя {user_id}"
            )
        else:  # reject
            await bot.send_message(user_id, "❌ К сожалению, ваша заявка отклонена.")
            await callback.message.edit_text(
                f"❌ Отклонено: @{callback.from_user.username or callback.from_user.first_name} "
                f"отклонил заявку пользователя {user_id}"
            )
        await callback.answer("✅ Действие выполнено")
    except Exception as e:
        logger.error(f"Ошибка при уведомлении пользователя {user_id}: {e}")
        await callback.answer("❌ Не удалось уведомить пользователя", show_alert=True)

# Webhook: запуск и остановка
async def on_startup(_=None):
    webhook_url = f"https://{HOST}/webhook"
    try:
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
        logger.info(f"Webhook установлен: {webhook_url}")
        # Проверяем текущий webhook
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Текущий webhook: {webhook_info.url}")
    except Exception as e:
        logger.error(f"Ошибка при установке webhook: {e}")
        raise

async def on_shutdown(_=None):
    try:
        # Закрываем сессию бота
        if bot.session and not bot.session.closed:
            await bot.session.close()
            logger.info("Сессия бота закрыта")
        await bot.delete_webhook()
        logger.info("Webhook удалён")
    except Exception as e:
        logger.error(f"Ошибка при завершении работы: {e}")

# Запуск aiohttp приложения
async def run_app():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path='/webhook')
    setup_application(app, dp, bot=bot)
    port = int(os.getenv("PORT", 10000))
    logger.info(f"Запуск приложения на порту {port}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Приложение запущено на http://0.0.0.0:{port}")
    return runner

async def main():
    try:
        runner = await run_app()
        # Держим приложение запущенным
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Завершение работы приложения")
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {e}")
        raise
    finally:
        # Гарантируем закрытие сессии и webhook
        await on_shutdown()
        await runner.cleanup()
        logger.info("Приложение полностью остановлено")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске: {e}")
