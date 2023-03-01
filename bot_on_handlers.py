from json.decoder import JSONDecodeError

import aiohttp
import asyncio

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


ua_apikey = os.environ['UAAPIKEYß']

domen1 = os.environ['DOMEN1']
domen2 = os.environ['DOMEN2']
domen3 = os.environ['DOMEN3']


logging.basicConfig(filename='./bot.log', encoding='utf-8', level=logging.INFO)

API_TOKEN = os.environ['API_TOKEN']
bot = Bot(token=API_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# States
class Form(StatesGroup):
    arriving = State()
    arriving_polling = State()
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

kb_yes = [
    [
        types.KeyboardButton(text='DA'),
        types.KeyboardButton(text='PIZDA')
    ]
]
keyboard_yes = types.ReplyKeyboardMarkup(
    keyboard=kb_yes,
    resize_keyboard=True,
)


def get_user_agent():
    url = "https://api.apilayer.com/user_agent/generate?windows=windows&tablet=tablet&mobile=mobile&mac=mac&linux=linux&ie=ie&firefox=firefox&desktop=desktop&chrome=chrome&android=android"
    payload = {}
    headers = {f"apikey": {ua_apikey}}
    response = requests.request("GET", url, headers=headers, data=payload)
    result = response.text
    return result


@dp.message_handler(commands='start')
async def privet(message: types.Message, state: FSMContext):
    logging.info(f'{message}')

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


async def get_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=api_headers) as r:
            return await r.json()


@dp.message_handler(state=Form.arriving)
async def arriving_worker(message: types.Message, state: FSMContext):
    state_for_logs = 'arriving'
    logging.info(f'state: {state_for_logs} {message}')

    flight = message.text.strip().lower()

    try:
        url = f'https://{domen3}/clickhandler/?version=1.5&flight={flight}'
        json = await asyncio.create_task(get_json(url))

        try:
            try:
                status_text = json['status']['text']
            except KeyError:
                status_text = 'karoche libo ne v vozduhe libo ty huynyu prislal'
            await message.answer(f'{flight} status: {status_text}')

            scheduled_arrival_time_unix = json['time']['scheduled']['arrival']
            scheduled_arrival_time = datetime.fromtimestamp(
                scheduled_arrival_time_unix)
            await message.answer(f'{flight} Scheduled Arrival Time: {scheduled_arrival_time}')

            estimated_arrival_time_unix = json['time']['estimated']['arrival']
            if estimated_arrival_time_unix:
                estimated_arrival_time = datetime.fromtimestamp(
                    estimated_arrival_time_unix)
                await message.answer(f'{flight} Estimated Arrival Time: {estimated_arrival_time}')

                async with state.proxy() as data:
                    data['arriving_polling'] = flight

                await Form.arriving_polling.set()
                await message.answer('subscribe to change in estimated flight time?', reply_markup=keyboard_yes)

            real_arrival_time_unix = json['time']['real']['arrival']
            if real_arrival_time_unix:
                await message.answer(f'{flight} Flight landed! Real Arrival Time: {datetime.fromtimestamp(real_arrival_time_unix)}')
                await state.finish()

        except:  # fix me !!!
            await message.answer('invalid')
            await state.finish()

    except JSONDecodeError:
        await message.answer('invalid, net jsona')
        await state.finish()


@dp.message_handler(state=Form.arriving_polling)
async def arriving_worker2(message: types.Message, state: FSMContext):
    if message.text == 'DA':
        updates = True
    elif message.text == 'PIZDA':
        updates = False

    estimated_arrival_time_unix = 1  # bootstrap
    estimated_buffer = estimated_arrival_time_unix

    async with state.proxy() as data:
        flight = data['arriving_polling']
    await state.finish()

    url = f'https://{domen3}/clickhandler/?version=1.5&flight={flight}'

    while estimated_arrival_time_unix:
        if (abs(estimated_arrival_time_unix - estimated_buffer) > 300) and updates:
            await message.answer(f'{flight} Estimated Arrival Time: {datetime.fromtimestamp(estimated_arrival_time_unix)}', reply_markup=types.ReplyKeyboardRemove())
        estimated_buffer = estimated_arrival_time_unix

        json = await asyncio.create_task(get_json(url))
        estimated_arrival_time_unix = json['time']['estimated']['arrival']
        await asyncio.sleep(30)

        real_arrival_time_unix = json['time']['real']['arrival']
        if real_arrival_time_unix:
            await message.answer(f'{flight} Flight landed! Real Arrival Time: {datetime.fromtimestamp(real_arrival_time_unix)}')


@dp.message_handler(text='Track departing flight')
async def departing_privet(message: types.Message):
    await Form.departing.set()
    await message.reply('OK.  Пришли aircraft registration.', reply_markup=types.ReplyKeyboardRemove())


async def get_all_scheduled_flights(soup_headers, aircraft_registration):
    aircraft_history_url = f'https://{domen1}/data/aircraft/{aircraft_registration}'
    async with aiohttp.ClientSession() as session:
        async with session.get(aircraft_history_url, headers=soup_headers) as r:
            html = await r.text

    soup = BeautifulSoup(html, 'html.parser')

    all_flights = []
    flight_history_table = soup.find_all('tr', class_="data-row")
    for i in flight_history_table:
        for link in i.find('a', class_="fbold"):
            all_flights.append(link.text)

    return all_flights


@dp.message_handler(state=Form.departing)
async def departing_worker(message: types.Message, state: FSMContext):
    state_for_logs = 'departing'
    logging.info(f'state: {state_for_logs} {message}')

    aircraft_registration = message.text.strip()

    # all_flights = get_all_scheduled_flights(soup_headers, aircraft_registration)
    # print(all_flights)
    # flight = all_flights[0].lower()

    await message.answer(f'принял, чекаем когда взлетит {aircraft_registration}')
    await state.finish()

    url = f'https://{domen2}/zones/fcgi/feed.js?reg=!{aircraft_registration}'

    while True:
        json = await asyncio.create_task(get_json(url))
        if len(json) == 3:
            break
        await asyncio.sleep(30)

    await message.answer(f'{aircraft_registration} взлетел, flight: {list(json.keys())[2]}')


@dp.message_handler(text='Get history of a flight')
async def history_privet(message: types.Message):
    await Form.history.set()
    await message.reply('OK. Prishli flight.', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=Form.history)
async def history_worker(message: types.Message, state: FSMContext):
    state_for_logs = 'history'
    logging.info(f'state: {state_for_logs} {message}')

    flight = message.text.strip().lower()

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
    logging.info(f'state: {state_for_logs} {message}')
    state_for_logs = 'square'

    try:
        latitude, longitude = message.text.lower().strip().split()

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
