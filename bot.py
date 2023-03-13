from json.decoder import JSONDecodeError

import asyncio
import os
from datetime import datetime
import re
import logging
import json

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table

from bs4 import BeautifulSoup

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

from aiogram.utils.exceptions import MessageIsTooLong

# selfdefined
from make_request import make_requset
from db import get_user, put_user


load_dotenv()

domen1 = os.environ['DOMEN1']
domen2 = os.environ['DOMEN2']
domen3 = os.environ['DOMEN3']


logging.basicConfig(filename='bot.log', encoding='utf-8', level=logging.INFO)

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
        types.KeyboardButton(text='Track arriving aircraft'),
        types.KeyboardButton(text='Track departing aircraft')
    ],
    [
        types.KeyboardButton(text='Get history of a aircraft'),
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


@dp.message_handler(text='Track arriving aircraft')
async def arriving_privet(message: types.Message):
    await Form.arriving.set()
    await message.reply('OK. Пришли aircraft registration.', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=Form.arriving)
async def arriving_worker(message: types.Message, state: FSMContext):
    state_for_logs = 'arriving'
    logging.info(f'state: {state_for_logs} {message}')

    aircraft_registration = message.text.strip()

    try:
        url = f'https://{domen1}/v1/search/web/find?query={aircraft_registration}&limit=50'
        json = await asyncio.create_task(make_requset(url, 'json'))
    except JSONDecodeError:
        await message.answer('Invalid input. No JSON 2 data found.')
        await state.finish()
        return
    
    flight = json["results"][0]["id"]
    
    try:
        url = f'https://{domen3}/clickhandler/?version=1.5&flight={flight}'
        json = await asyncio.create_task(make_requset(url, 'json'))
    except JSONDecodeError:
        await message.answer('Invalid input. No JSON 2 data found.')
        await state.finish()
        return

    # Handle status
    try:
        status_text = json['status']['text']
    except KeyError:
        if len(json.keys()) == 1 and json['s']:
            status_text = 'Not in the air'
        else:
            status_text = 'Unknown error'
    await message.answer(f'{aircraft_registration} Status: {status_text}')

    # Handle scheduled arrival time
    scheduled_arrival_time_unix = json['time']['scheduled']['arrival']
    if json["airline"]["name"] == "Private owner" and scheduled_arrival_time_unix == 0:
        await message.answer('Private plane detected!')
    else:
        scheduled_arrival_time = datetime.fromtimestamp(
            scheduled_arrival_time_unix)
        await message.answer(f'{aircraft_registration} Scheduled Arrival Time: {scheduled_arrival_time}')

    # Handle estimated arrival time
    estimated_arrival_time_unix = json['time']['estimated']['arrival']
    if estimated_arrival_time_unix:
        estimated_arrival_time = datetime.fromtimestamp(
            estimated_arrival_time_unix)
        await message.answer(f'{aircraft_registration} Estimated Arrival Time: {estimated_arrival_time}')

        async with state.proxy() as data:
            data['arriving_polling'] = flight

        await Form.arriving_polling.set()
        await message.answer('Subscribe to change in estimated flight time?', reply_markup=keyboard_yes)

    # Handle real arrival time
    real_arrival_time_unix = json['time']['real']['arrival']
    if real_arrival_time_unix:
        await message.answer(f'{aircraft_registration} Flight landed! Real Arrival Time: {datetime.fromtimestamp(real_arrival_time_unix)}')
        await state.finish()


@dp.message_handler(state=Form.arriving_polling)
async def arriving_worker2(message: types.Message, state: FSMContext):
    if message.text == 'DA':
        updates = True
    elif message.text == 'PIZDA':
        updates = False

    async with state.proxy() as data:
        flight = data['arriving_polling']
    await state.finish()

    url = f'https://{domen3}/clickhandler/?version=1.5&flight={flight}'

    estimated_arrival_time_unix = 1  # bootstrap
    estimated_buffer = 0

    time_difference = 300

    while estimated_arrival_time_unix:
        json = await asyncio.create_task(make_requset(url, 'json'))
        estimated_arrival_time_unix = json['time']['estimated']['arrival']

        if abs(estimated_arrival_time_unix - estimated_buffer) > time_difference and updates:
            await message.answer(f'Estimated Arrival Time: {datetime.fromtimestamp(estimated_arrival_time_unix)}', reply_markup=types.ReplyKeyboardRemove())

        estimated_buffer = estimated_arrival_time_unix
        await asyncio.sleep(30)

        real_arrival_time_unix = json['time']['real']['arrival']
        if real_arrival_time_unix:
            await message.answer(f'Flight landed! Real Arrival Time: {datetime.fromtimestamp(real_arrival_time_unix)}')


@dp.message_handler(text='Track departing flight')
async def departing_privet(message: types.Message):
    await Form.departing.set()
    await message.reply('OK. Пришли aircraft registration.', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=Form.departing)
async def departing_worker(message: types.Message, state: FSMContext):
    state_for_logs = 'departing'
    logging.info(f'state: {state_for_logs} {message}')

    aircraft_registration = message.text.strip()

    await message.answer(f'Принял, чекаем когда взлетит {aircraft_registration}')
    await state.finish()

    url = f'https://{domen2}/zones/fcgi/feed.js?reg=!{aircraft_registration}'

    try:
        while True:
            json = await asyncio.create_task(make_requset(url, 'json'))
            if len(json) == 3:
                break
            await asyncio.sleep(30)
    except Exception as e:
        logging.exception(f"Error in departing_worker: {e}")
        await message.answer(f"Error occurred while processing your request. Please try again later.")
        return

    try:
        flight_number = list(json.keys())[2]
        await message.answer(f'{aircraft_registration} в воздухе, flight: {flight_number}')
    except Exception as e:
        logging.exception(f"Error while processing JSON response: {e}")
        await message.answer("Error occurred while processing the response. Please try again later.")
        return


class AircraftDataNotFoundError(Exception):
    pass


def extract_aircraft_table(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Find the table with the specified ID
    table = soup.find('table', {'id': 'tbl-datatable'})
    table_html = str(table)
    soup = BeautifulSoup(table_html, 'html.parser')

    table_data = []

    # Extract the header row
    header_row = []
    for th in soup.thead.tr.find_all('th', attrs={'class': 'hidden-xs hidden-sm'}):
        header_row.append(th.get_text(strip=True))
    headers = [h for h in header_row if h.strip()]
    table_data.append(headers)

    # Get table rows
    for tr in soup.tbody.find_all('tr'):
        row_data = list((td.get_text(strip=True) for td in tr.find_all('td', attrs={
                        'class': CLASS_PATTERN}) if not td.find('a', attrs={'class': A_PATTERN})))
        data = [i for i in row_data if i.strip()]
        table_data.append(data)

    return table_data


CLASS_PATTERN = re.compile(r'(^|\s)hidden-xs hidden-sm$')
A_PATTERN = re.compile(r'btn.*')


def create_aircraft_table_pdf(table):
    document = SimpleDocTemplate("./report.pdf", pagesize=A4)
    items = []
    t = Table(table)
    items.append(t)
    document.build(items)
    return document


@dp.message_handler(text='Get history of a aircraft')
async def get_aircraft_history(message: types.Message):
    await Form.history.set()
    await message.reply('Please enter the registration number:', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=Form.history)
async def handle_aircraft_history_request(message: types.Message, state: FSMContext):
    registration_number = message.text.strip().lower()
    logging.info(f'state: history {message}')

    url = f'https://{domen1}/data/aircraft/{registration_number}'
    html = await asyncio.create_task(make_requset(url, 'text'))

    try:
        table = extract_aircraft_table(html)
        with open("report.pdf", "x") as f:
            pass
        create_aircraft_table_pdf(table)
        await message.answer_document(open("./report.pdf", 'rb'))

    except AircraftDataNotFoundError:
        await message.answer(f'No data available for aircraft {registration_number}. Please check the aircraft identifier and try again.')

    finally:
        os.remove("./report.pdf")
        await state.finish()


@dp.message_handler(text='Check for live planes in the square')
async def square_privet(message: types.Message):
    await Form.square.set()
    await message.reply('Please send me four coordinates separated by spaces', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=Form.square)
async def square_worker(message: types.Message, state: FSMContext):
    logging.info(f'state: square {message.text}')

    try:
        latitude1, longitude1, latitude2, longitude2 = message.text.lower().strip().split()

    except ValueError:
        await message.answer('Брат, ты написал хуйню, попробуй ещё раз. Мне нужны координаты, четыре числа через пробел')
        await state.finish()
        return

    url = f'https://{domen2}/zones/fcgi/feed.js?faa=1&bounds={latitude1}%2C{longitude1}%2C{latitude2}%2C{longitude2}&satellite=1&mlat=1&flarm=1&adsb=1&gnd=1&air=1&vehicles=1&estimated=1&maxage=14400&gliders=1&stats=1'

    try:
        json = await asyncio.create_task(make_requset(url, 'json'))
        flights = list(json.keys())
        aircrafts = [json[i][9] for i in flights if i not in ("stats", "full_count", "version") and json[i][9]]
        
        try:
            await message.answer(aircrafts)
        except MessageIsTooLong:
            with open("list.txt", "w") as f:
                for i in aircrafts:
                    f.write(f'{i} \n')
            await message.answer_document(open("./list.txt", 'rb'))

    except KeyError:
        await message.answer('Oops, something went wrong. Please try again later.')

    finally:
        await state.finish()
        os.remove("./list.txt")


@dp.message_handler(commands=['cancel'], state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.reply('You have no active requests.')
        return

    logging.info(f'Cancelling state {current_state} for {message.chat.id}')

    await state.finish()
    await message.reply('Request cancelled. How can I help you?', reply_markup=keyboard)


if __name__ == '__main__':

    executor.start_polling(dp, skip_updates=True)
