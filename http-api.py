# Импортируем необходимые классы.
import json
import logging

import aiohttp
import requests
from telegram.ext import Application, MessageHandler, filters
from telegram.ext import ApplicationBuilder

# from config import BOT_TOKEN

proxy_url = "socks5://user:pass@host:5000"

app = ApplicationBuilder().token('6709453503:AAHl9zSGGKuZ8Cr1CQhTFbt8YEbUhHVSV2s').proxy_url(proxy_url).build()

# Запускаем логгирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)


async def geocoder(update, context):
    geocoder_uri = "http://geocode-maps.yandex.ru/1.x/"
    response = await get_response(geocoder_uri, params={
        "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
        "format": "json",
        "geocode": update.message.text
    })

    toponym = response["response"]["GeoObjectCollection"][
        "featureMember"][0]["GeoObject"]
    ll, spn = get_ll_spn(toponym)

    static_api_request = f"http://static-maps.yandex.ru/1.x/?ll={ll}&spn={spn}&l=map"
    await context.bot.send_photo(
        update.message.chat_id,  # Идентификатор чата. Куда посылать картинку.
        # Ссылка на static API, по сути, ссылка на картинку.
        # Телеграму можно передать прямо её, не скачивая предварительно карту.
        static_api_request,
        caption="Нашёл:"
    )


def get_ll_spn(toponym):
    # url, по которому доступно API Яндекс.Карт
    url = "https://geocode-maps.yandex.ru/1.x/"
    # параметры запроса
    # отправляем запрос
    # получаем JSON ответа
    # получаем координаты города
    # (там написаны долгота(longitude), широта(latitude) через пробел)
    # посмотреть подробное описание JSON-ответа можно
    # в документации по адресу https://tech.yandex.ru/maps/geocoder/
    coordinates_str = toponym['Point']['pos']
    # Превращаем string в список, так как
    # точка - это пара двух чисел - координат
    long, lat = list(map(float, coordinates_str.split()))
    return f'{long},{lat}', f'0.01,0.01'


async def get_response(url, params):
    logger.info(f"getting {url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            return await resp.json()


def main():
    # Создаём объект Application.
    # Вместо слова "TOKEN" надо разместить полученный от @BotFather токен
    text_handler = MessageHandler(filters.TEXT, geocoder)
    application = Application.builder().token('6681675964:AAE95MFclBEzDY9NSg0SZfzLtDiM_EG1yZo').build()
    application.add_handler(text_handler)
    application.run_polling()


# Запускаем функцию main() в случае запуска скрипта.
if __name__ == '__main__':
    main()
