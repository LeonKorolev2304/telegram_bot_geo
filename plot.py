# Импортируем необходимые классы.
import logging
from telegram.ext import Application, MessageHandler, filters, ConversationHandler
from telegram.ext import ApplicationBuilder
from telegram.ext import CommandHandler
# from config import BOT_TOKEN

proxy_url = "socks5://user:pass@host:5000"

app = ApplicationBuilder().token('6709453503:AAHl9zSGGKuZ8Cr1CQhTFbt8YEbUhHVSV2s').proxy_url(proxy_url).build()

# Запускаем логгирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)


async def start(update, context):
    await update.message.reply_text(
        "Привет. Пройдите небольшой опрос, пожалуйста!\n"
        "Вы можете прервать опрос, послав команду /stop.\n"
        "В каком городе вы живёте?")

    # Число-ключ в словаре states —
    # втором параметре ConversationHandler'а.
    return 1
    # Оно указывает, что дальше на сообщения от этого пользователя
    # должен отвечать обработчик states[1].
    # До этого момента обработчиков текстовых сообщений
    # для этого пользователя не существовало,
    # поэтому текстовые сообщения игнорировались.


# Добавили словарь user_data в параметры.
async def first_response(update, context):
    # Сохраняем ответ в словаре.
    context.user_data['locality'] = update.message.text
    await update.message.reply_text(
        f"Какая погода в городе {context.user_data['locality']}?")
    return 2


# Добавили словарь user_data в параметры.
async def second_response(update, context):
    weather = update.message.text
    logger.info(weather)
    # Используем user_data в ответе.
    await update.message.reply_text(
        f"Спасибо за участие в опросе! Привет, {context.user_data['locality']}!")
    context.user_data.clear()  # очищаем словарь с пользовательскими данными
    return ConversationHandler.END

async def stop(update, context):
    await update.message.reply_text("Всего доброго!")
    return ConversationHandler.END


def main():
    # Создаём объект Application.
    # Вместо слова "TOKEN" надо разместить полученный от @BotFather токен
    application = Application.builder().token('7179344213:AAECLDzeQL3xNgAaSvZ9vDbwfVbxe0oy_88').build()
    conv_handler = ConversationHandler(
        # Точка входа в диалог.
        # В данном случае — команда /start. Она задаёт первый вопрос.
        entry_points=[CommandHandler('start', start)],

        # Состояние внутри диалога.
        # Вариант с двумя обработчиками, фильтрующими текстовые сообщения.
        states={
            # Функция читает ответ на первый вопрос и задаёт второй.
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_response)],
            # Функция читает ответ на второй вопрос и завершает диалог.
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, second_response)]
        },

        # Точка прерывания диалога. В данном случае — команда /stop.
        fallbacks=[CommandHandler('stop', stop)]
    )

    application.add_handler(conv_handler)
    application.run_polling()


# Запускаем функцию main() в случае запуска скрипта.
if __name__ == '__main__':
    main()