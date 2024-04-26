import logging
import math
import sqlite3

import aiohttp
import requests
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from telegram.ext import ApplicationBuilder

proxy_url = "socks5://user:pass@host:5000"

app = ApplicationBuilder().token('6709453503:AAHl9zSGGKuZ8Cr1CQhTFbt8YEbUhHVSV2s').proxy_url(proxy_url).build()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

reply_keyboard = [['/start', '/help', '/close']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)


async def start(update, context):
    user = update.effective_user
    await update.message.reply_html(
        rf'Привет {user.mention_html()}! Я гео-бот, напишите мне адрес и организацию, и я найду для вас ближайшую к ' +
        'этому адресу организацию.',
        reply_markup=markup
    )


async def help_command(update, context):
    await update.message.reply_text('Напишите мне сообщение типа "[Адрес] : [Организация]" (пробелы до и после ' +
                                    'двоеточия обязательны!). На карте синим отмечен ваш адрес, а зелёным — ' +
                                    'ближайшая организация.', reply_markup=markup)


async def close_keyboard(update, context):
    await update.message.reply_text(
        "Всегда пожалуйста",
        reply_markup=ReplyKeyboardRemove()
    )


async def geocoder(update, context):
    mes = update.message.text.split(' : ')
    upd = '_'.join(update.message.text.split(' : '))
    con = sqlite3.connect("yandex_maps.sqlite")
    cur = con.cursor()
    result = cur.execute(f"""SELECT * FROM maps
                WHERE request = '{upd}'""").fetchall()
    if not result:
        try:
            address, company = mes[0], mes[1]
            response = requests.get(
                f"http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f-0493-4b70-98ba-98533de7710"
                f"b&geocode={address}&format=json").json()
            toponym = response["response"]["GeoObjectCollection"][
                "featureMember"][0]["GeoObject"]
            ll, spn = get_ll_spn(toponym)
            search_api_server = "https://search-maps.yandex.ru/v1/"
            api_key = "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3"

            address_ll = tuple(map(float, ll.split(',')))

            search_params = {
                "apikey": api_key,
                "text": company,
                "lang": "ru_RU",
                "ll": ll,
                "type": "biz"
            }

            topo_response = requests.get(search_api_server, params=search_params)

            json_topo_response = topo_response.json()

            organization = json_topo_response["features"][0]
            org_name = organization["properties"]["CompanyMetaData"]["name"]
            org_address = organization["properties"]["CompanyMetaData"]["address"]

            point = organization["geometry"]["coordinates"]
            distance = get_distance(address_ll, point)
            delta = str(distance / 111 + distance / 111 * 0.75)

            map_params = {
                "ll": f'{point[0]},{point[1]}',
                "spn": ",".join([delta, delta]),
                "pt": f"{point[0]},{point[1]},pm2dgl~{address_ll[0]},{address_ll[1]},pm2lbl"
            }

            static_api_request = f"http://static-maps.yandex.ru/1.x/?ll={ll}&spn={map_params['spn']}&" \
                                 f"l=map&pt={map_params['pt']}"
            cur.execute(
                f"""INSERT INTO maps(request, ll, spn, pt, company, address, distance) VALUES('{upd}', '{ll}',
                '{map_params['spn']}', '{map_params['pt']}', '{org_name}', '{org_address}', '{str(distance)}')""")
            con.commit()
            con.close()
            await context.bot.send_photo(
                update.message.chat_id,
                static_api_request,
                caption=f'Нашёл: "{org_name}",\n{org_address}.\nВам идти {str(round(float(distance) * 1000, 1))} м.'
            )
        except Exception:
            await update.message.reply_text("Ничего не найдено.")
    else:
        ll = cur.execute(f"""SELECT ll FROM maps
                        WHERE request = '{upd}'""").fetchone()[0]
        spn = cur.execute(f"""SELECT spn FROM maps
                        WHERE request = '{upd}'""").fetchone()[0]
        pt = cur.execute(f"""SELECT pt FROM maps
                        WHERE request = '{upd}'""").fetchone()[0]
        org_name = cur.execute(f"""SELECT company FROM maps
                WHERE request = '{upd}'""").fetchone()[0]
        org_address = cur.execute(f"""SELECT address FROM maps
                WHERE request = '{upd}'""").fetchone()[0]
        distance = cur.execute(f"""SELECT distance FROM maps
                        WHERE request = '{upd}'""").fetchone()[0]
        static_api_request = f"http://static-maps.yandex.ru/1.x/?ll={ll}&spn={spn}&l=map&pt={pt}"
        con.close()
        await context.bot.send_photo(
            update.message.chat_id,
            static_api_request,
            caption=f'''Вы уже находили: "{org_name}",\n{org_address}.\nВам идти {str(round(float(distance) * 1000, 1))}
            м.'''
        )


def get_ll_spn(toponym):
    coordinates_str = toponym['Point']['pos']
    long, lat = list(map(float, coordinates_str.split()))
    return f'{long},{lat}', f'0.01,0.01'


def get_distance(p1, p2):
    # p1 и p2 - это кортежи из двух элементов - координаты точек
    radius = 6373.0

    lon1 = math.radians(p1[0])
    lat1 = math.radians(p1[1])
    lon2 = math.radians(p2[0])
    lat2 = math.radians(p2[1])

    d_lon = lon2 - lon1
    d_lat = lat2 - lat1

    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    c = 2 * math.atan2(a ** 0.5, (1 - a) ** 0.5)

    distance = radius * c
    return distance


async def get_response(url, params):
    logger.info(f"getting {url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            return await resp.json()


def main():
    text_handler = MessageHandler(filters.TEXT, geocoder)
    application = Application.builder().token('6681675964:AAE95MFclBEzDY9NSg0SZfzLtDiM_EG1yZo').build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("close", close_keyboard))
    application.add_handler(text_handler)
    application.run_polling()


if __name__ == '__main__':
    main()
