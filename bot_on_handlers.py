import os

from pprint import pprint

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

import requests
from datetime import datetime
import time
import math

from bs4 import BeautifulSoup

import random

import logging


import aiogram.utils.markdown as md

from aiogram import Bot, Dispatcher, types

from aiogram.contrib.fsm_storage.memory import MemoryStorage

from aiogram.dispatcher import FSMContext

from aiogram.dispatcher.filters import Text

from aiogram.dispatcher.filters.state import State, StatesGroup

from aiogram.types import ParseMode

from aiogram.utils import executor


from proxie import get_webshare_proxies_list, make_get_request_with_proxie
from db import get_user, put_user, put_message


domen1 = os.environ['DOMEN1']
domen2 = os.environ['DOMEN2']
domen3 = os.environ['DOMEN3']

# headers_arriva = {
#     'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
#     'Accept-Encoding': 'gzip, deflate, br',
#     'Accept-Language': 'en-US,en;q=0.5',
#     'Connection': 'keep-alive',
#     'Cookie': 'showAds=yes; OptanonConsent=isIABGlobal=false&datestamp=Sun+Nov+27+2022+19%3A17%3A05+GMT%2B0300+(Moscow+Standard+Time)&version=202210.1.0&hosts=&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&geolocation=RU%3BSPE&AwaitingReconsent=false; OptanonAlertBoxClosed=2022-11-27T16:17:05.,131Z; __cfruid=52b8df4dc84fc6a2a7c1375b3c7a723ff9dfcd79-1669047322;',
#     'DNT': '1',
#     'Host': 'data-live.flightradar24.com',
#     'Sec-Fetch-Dest': 'document',
#     'Sec-Fetch-Mode': 'navigate',
#     'Sec-Fetch-Site': 'cross-site',
#     'TE': 'trailers',
#     'Upgrade-Insecure-Requests': '1',
#     'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0'
# }

soup_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'utf-8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Cookie': 'showAds=yes; OptanonConsent=isIABGlobal=false&datestamp=Mon+Nov+21+2022+19%3A19%3A07+GMT%2B0300+(Moscow+Standard+Time)&version=202210.1.0&hosts=landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&geolocation=RU%3BSPE&AwaitingReconsent=false; OptanonAlertBoxClosed=2022-11-21T16:19:07.213Z; __cfruid=52b8df4dc84fc6a2a7c1375b3c7a723ff9dfcd79-1669047322;',
    'DNT': '1',
    'Host': 'www.flightradar24.com',
    'If-Modified-Since': 'Mon, 21 Nov 2022 16:19:06 GMT',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'ame-origin',
    'Sec-Fetch-User': '?1',
    'TE': 'trailers',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0'
}

api_headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0',
}


logging.basicConfig(level=logging.INFO)

API_TOKEN = os.environ['API_TOKEN']


bot = Bot(token=API_TOKEN)


# For example use simple MemoryStorage for Dispatcher.

storage = MemoryStorage()

dp = Dispatcher(bot, storage=storage)


# States
class Form(StatesGroup):
    arriving = State()
    departing = State()
    history = State()
    square = State()


kb = [
    [
        types.KeyboardButton(text='Track arriving flight'),
        types.KeyboardButton(text='Track departing flight')
    ],
    [
        types.KeyboardButton(text='Get history of a flight'),
        types.KeyboardButton(text='Check for live planes in the square')
    ]
]
keyboard = types.ReplyKeyboardMarkup(
    keyboard=kb,
    resize_keyboard=True,
    input_field_placeholder='Chto vam nado??'
)


@dp.message_handler(commands='start')
async def privet(message: types.Message, state: FSMContext):
    user_id = message['from']['id']
    user = get_user(user_id)
    if not user:
        first_name = message['from']['first_name']
        username = message['from']['username']
        put_user(user_id, first_name, username)

    await message.answer('privet, che hochesh?', reply_markup=keyboard)


@dp.message_handler(text='Track arriving flight')
async def arriving_privet(message: types.Message):
    await Form.arriving.set()
    await message.reply('OK. Пришли flight.', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=Form.arriving)
async def arriving_worker(message: types.Message, state: FSMContext):
    date = message['date']
    text = message.text
    state_for_logs = 'arriving'
    user_id = message['from']['id']
    put_message(date, text, state_for_logs, user_id)

    flight = text

    url = f'https://{domen3}/clickhandler/?version=1.5&flight={flight}'
    r = requests.get(url)

    try:
        json = r.json()
        try:
            status_text = json['status']['text']
        except KeyError:
            status_text = 'karoche libo ne v vozduhe libo ty huynyu prislal'
        await message.answer(f'status: {status_text}')

        scheduled_arrival_time_unix = json['time']['scheduled']['arrival']
        scheduled_arrival_time = datetime.fromtimestamp(
            scheduled_arrival_time_unix)
        await message.answer(f'Scheduled Arrival Time: {scheduled_arrival_time}')

        estimated_arrival_time_unix = json['time']['estimated']['arrival']
        if estimated_arrival_time_unix:
            await message.answer(f'Estimated Arrival Time: {datetime.fromtimestamp(estimated_arrival_time_unix)}')

        #     # answer = input(
        #     #     'subscribe to change in estimated flight time? y for yeas, n for no \n')
        #     # if answer == 'y':
        #     #     updates = True
        #     # elif answer == 'n':
        #     #     updates = False
        #     # else:
        #     #     print('ti eblan, delay reboot')

        #     updates = True

        #     estimated_buffer = estimated_arrival_time_unix

        # while estimated_arrival_time_unix:
        #     if updates:
        #         if abs(estimated_arrival_time_unix - estimated_buffer) > 300:
        #             await message.answer(f'Estimated Arrival Time: {datetime.fromtimestamp(estimated_arrival_time_unix)}')
        #         estimated_buffer = estimated_arrival_time_unix
        #     json = get_json(bortovoy, headers_arriva)
        #     estimated_arrival_time_unix = json['time']['estimated']['arrival']
        #     time.sleep(30)

        real_arrival_time_unix = json['time']['real']['arrival']
        if real_arrival_time_unix:
            await message.answer(f'Flight landed! Real Arrival Time: {datetime.fromtimestamp(real_arrival_time_unix)}')

    except:
        await message.answer('invalid')
    finally:
        await state.finish()


@dp.message_handler(text='Track departing flight')
async def departing_privet(message: types.Message):
    await Form.departing.set()
    await message.reply('OK.  Пришли flight.', reply_markup=types.ReplyKeyboardRemove())


def get_all_scheduled_flights(soup_headers, aircraft_registration):
    aircraft_history_url = f'https://{domen1}/data/aircraft/{aircraft_registration}'
    r = requests.get(aircraft_history_url, headers=soup_headers)
    html = r.text
    soup = BeautifulSoup(html, 'html.parser')
    
    all_flights = []
    flight_history_table = soup.find_all('tr', class_="data-row")
    for i in flight_history_table:
        for link in i.find('a', class_="fbold"):
            all_flights.append(link.text)

    return all_flights


def get_json_departing(api_headers, flight):
    api_url = f'https://{domen2}/zones/fcgi/feed.js?reg=!{flight}'
    print(api_url)
    r = requests.get(api_url, headers=api_headers)
    json = r.json()
    return json


@dp.message_handler(state=Form.departing)
async def departing_worker(message: types.Message, state: FSMContext):
    date = message['date']
    text = message.text
    state_for_logs = 'departing'
    user_id = message['from']['id']
    put_message(date, text, state_for_logs, user_id)

    aircraft_registration = text

    all_flights = get_all_scheduled_flights(soup_headers, aircraft_registration)

    try:
        flight = all_flights[0].lower()

        json = get_json_departing(api_headers, flight)

        await message.answer('Принял запрос. Сейчас эта функция не работает. Но в последсвии тебе будет приходить сообщение когда самолёт взлетит.')

        # while len(json) == 2:
        #     json = get_json_departing(api_headers, flight)
        #     time.sleep(30)

        # await message.answer('on vzletel')
    
    except IndexError:
        await message.answer('invalid')

    finally:
        await state.finish()


@dp.message_handler(text='Get history of a flight')
async def history_privet(message: types.Message):
    await Form.history.set()
    await message.reply('OK. Prishli flight.', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=Form.history)
async def history_worker(message: types.Message, state: FSMContext):
    date = message['date']
    text = message.text
    state_for_logs = 'history'
    user_id = message['from']['id']
    put_message(date, text, state_for_logs, user_id)

    flight = text

    url = f'https://{domen1}/data/flights/{flight}'

    api_headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0',
    }

    proxies = get_webshare_proxies_list()

    r = make_get_request_with_proxie(
        url=url, proxies_list=proxies, headers=api_headers)

    html = r.text

    soup = BeautifulSoup(html, 'html.parser')

    flight_table = soup.find(id="tbl-datatable")

    try:
        titles = []
        for i in flight_table.thead.tr.find_all(class_="hidden-xs hidden-sm"):
            title = i.string
            if title:
                titles.append(title)

        table = []
        table.append(titles)

        for tr in flight_table.tbody.find_all('tr'):
            content = []
            for td in tr.find_all('td'):
                if td['class'] == ['text-center-sm', 'hidden-xs', 'hidden-sm']:
                    content.append(td.contents[0].strip())
                elif td['class'] == ['hidden-xs', 'hidden-sm']:
                    if td.div:
                        continue
                    string = td.string
                    if string:
                        content.append(string.strip())
                    else:
                        content.append(None)

            table.append(content)

        with open("test.pdf", "x") as f:
            pass

        document = SimpleDocTemplate("./test.pdf", pagesize=A4)
        items = []
        t = Table(table)
        items.append(t)
        document.build(items)

        await message.answer_document(open("./test.pdf", 'rb'))

        os.remove("test.pdf")

    except AttributeError:
        nope = soup.find('div', attrs={
                         "class": "row p-t-10 text-center", "style": "padding:10px 0;font-weight:700"})
        try:
            nope_msg = str(nope.contents[0]).strip()
            if nope_msg == 'There is currently no data available for your request':
                await message.answer(f'Не найдено данных по запросу {flight}. Проверь правильность идентификатора рейса.')
            else:
                await message.answer('Подозрительные неполадки')
        except AttributeError:
            await message.answer('Подозрительные неполадки')

    finally:
        await state.finish()


@dp.message_handler(text='Check for live planes in the square')
async def square_privet(message: types.Message):
    await Form.square.set()
    await message.reply('OK. Prishli koordy.', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=Form.square)
async def square_worker(message: types.Message, state: FSMContext):
    date = message['date']
    text = message.text
    state_for_logs = 'square'
    user_id = message['from']['id']
    put_message(date, text, state_for_logs, user_id)

    try:
        latitude, longitude = text.split()

        square_url = f'https://{domen2}/zones/fcgi/feed.js?faa=1&bounds={latitude}%2C{longitude}%2C27.731%2C28.389&satellite=1&mlat=1&flarm=1&adsb=1&gnd=1&air=1&vehicles=1&estimated=1&maxage=14400&gliders=1&stats=1'

        api_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0',
        }

        proxies = get_webshare_proxies_list()

        r = make_get_request_with_proxie(
            url=square_url, proxies_list=proxies, headers=api_headers)
        json = r.json()

        # full_count = json['full_count']
        # all_planes = list(json.keys())[2:]

        await message.answer(f"сейчас летает {json['stats']['total']['ads-b']} самолётов")
    
    except ValueError:
        await message.answer('Брат, ты написал хуйню, попробуй ещё раз. Мне нужны координаты, два числа')

    finally:
        await state.finish()


if __name__ == '__main__':

    executor.start_polling(dp, skip_updates=True)
