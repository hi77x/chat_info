
import logging
import redis
from datetime import datetime
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButtonRequestChat,
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    KeyboardButtonRequestUsers
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO  # Уровень INFO покажет все сообщения INFO и выше (WARNING, ERROR)
)
logger = logging.getLogger(__name__)

# Токен вашего бота (замените на новый токен после его генерации)
TOKEN = '7828754119:AAH2CD56qHfq4gjcy20v5HOjPRALDhlnprI'  # Обязательно замените на ваш новый токен

# Подключение к Redis
REDIS_URL = 'redis://default:nBpmtWTyNbcbiJkfDEratHRWzoWUTomE@autorack.proxy.rlwy.net:51766'

try:
    redis_client = redis.Redis.from_url(REDIS_URL)
    # Проверка подключения
    redis_client.ping()
    logger.info("Успешное подключение к Redis.")
except Exception as e:
    logger.error(f"Не удалось подключиться к Redis: {e}")
    redis_client = None  # В дальнейшем можно обработать отсутствие подключения

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"Получена команда /start от пользователя {user.id} ({user.username})")

    # Определите статус премиум пользователя (это просто пример)
    is_premium = user.is_premium if hasattr(user, 'is_premium') else False  # Используйте ваш способ определения статуса

    # Сохранение информации о пользователе в Redis
    if redis_client:
        try:
            user_key = f"user:{user.id}"
            user_data = {
                "username": user.username or "",
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "language_code": user.language_code or "",
                "joined_at": datetime.utcnow().isoformat(),
                "is_premium": str(is_premium)  # Преобразуем в строку
            }
            redis_client.hset(user_key, mapping=user_data)
            logger.info(f"Информация о пользователе {user.id} сохранена в Redis.")
        except Exception as e:
            logger.error(f"Ошибка при сохранении пользователя {user.id} в Redis: {e}")
    else:
        logger.warning("Redis клиент не инициализирован. Информация о пользователе не была сохранена.")

    keyboard = [
        [
            KeyboardButton(
                text="Chat",
                request_chat=KeyboardButtonRequestChat(
                    request_id=1,
                    chat_is_channel=False
                )
            ),
            KeyboardButton(
                text="Channel",
                request_chat=KeyboardButtonRequestChat(
                    request_id=2,
                    chat_is_channel=True
                )
            )
        ],
        [
            KeyboardButton(
                text="User",
                request_users=KeyboardButtonRequestUsers(
                    request_id=3,
                    user_is_bot=False
                )
            ),
            KeyboardButton(
                text="Bot",
                request_users=KeyboardButtonRequestUsers(
                    request_id=4,
                    user_is_bot=True
                )
            )
        ]
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=True
    )



    premium_status = "Premium: ✅" if is_premium else "Premium: ❌"
      
    username = user.username if user.username else None

    if username:
        user_link = f"[{user.first_name}](tg://user?id=5257346505)"
    else:
        user_link = user.first_name or "пользователь"

    await update.message.reply_text(
    f"Привет, {user_link}!\n\n"
    f"Твой ID: `{user.id}`\n"
    f"{premium_status}\n\n"
    '',
    reply_markup=reply_markup,
    parse_mode=ParseMode.MARKDOWN,
    disable_web_page_preview=True
)

    

# Обработка выбранных объектов и возврат ID
async def handle_selection_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    user = update.effective_user
    logger.info(f"Получено сообщение от пользователя {user.id} ({user.username}): {message.text}")

    response = None
    # Обработка выбора чата или канала через chat_shared
    if message.chat_shared:
        chat_id = message.chat_shared.chat_id
        logger.info(f"Пользователь выбрал чат с ID: {chat_id}")
        response = f"ID чата: `{chat_id}`"

    # Обработка выбора пользователя или бота через users_shared
    elif message.users_shared and message.users_shared.users:
        user_entries = []
        for shared_user in message.users_shared.users:
            user_id = shared_user.user_id
            user_entries.append(f"ID пользователя/бота: `{user_id}`")
            logger.info(f"Пользователь выбрал пользователя/бота с ID: {user_id}")
        response = "\n".join(user_entries)

    else:
        # Обработка случаев, когда сообщение не связано с выбором через кнопки запросов
        response = "Не удалось определить тип объекта. Пожалуйста, используйте кнопки выше для выбора."
        logger.warning(f"Не удалось определить тип объекта в сообщении от пользователя {user.id} ({user.username})")

    if response:
        try:
            await message.reply_text(
                response,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Отправлен ответ пользователю {user.id} ({user.username}): {response}")
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {user.id} ({user.username}): {e}")
    else:
        await message.reply_text(
            "Произошла неожиданная ошибка. Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.warning(f"Произошла неожиданная ошибка при обработке сообщения от пользователя {user.id} ({user.username})")

# Обработчик ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Ошибка при обработке обновления:", exc_info=context.error)
    # Можно отправить сообщение пользователю о возникновении ошибки, если необходимо
    if isinstance(update, Update) and update.message:
        try:
            await update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")
        except Exception as e:
            logger.error("Не удалось отправить сообщение об ошибке пользователю.", exc_info=e)

# Главная функция для запуска бота
def main() -> None:
    # Создаём приложение
    application = ApplicationBuilder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    
    # Обработчик для выбора чата/канала/пользователя/бота
    application.add_handler(MessageHandler(
        ~filters.COMMAND,  # Обрабатываем все сообщения, не являющиеся командами
        handle_selection_response
    ))

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    logger.info("Бот запущен и начал опрос серверов Telegram.")
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
