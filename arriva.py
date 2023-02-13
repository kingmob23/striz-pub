import requests
from datetime import datetime
import time
import math
import os


def get_json(flight, headers):
    print('!!! TEPET TUT !!!')
    url = f'https://{domen3}/clickhandler/?version=1.5&flight={flight}'
    print(url)
    r = requests.get(url, headers=headers)
    json = r.json()
    return json


def do_arriva(flight, headers):
    json = get_json(flight, headers)

    status_text = json['status']['text']
    print('status: ', status_text)

    scheduled_arrival_time_unix = json['time']['scheduled']['arrival']
    scheduled_arrival_time = datetime.fromtimestamp(
        scheduled_arrival_time_unix)
    print('Scheduled Arrival Time: ', scheduled_arrival_time)

    estimated_arrival_time_unix = json['time']['estimated']['arrival']
    if estimated_arrival_time_unix:
        print('Estimated Arrival Time: ', datetime.fromtimestamp(
            estimated_arrival_time_unix))

        answer = input(
            'subscribe to change in estimated flight time? y for yeas, n for no \n')
        if answer == 'y':
            updates = True
        elif answer == 'n':
            updates = False
        else:
            print('ti eblan, delay reboot')

        estimated_buffer = estimated_arrival_time_unix

    while estimated_arrival_time_unix:
        if updates:
            if abs(estimated_arrival_time_unix - estimated_buffer) > 300:
                print('Estimated Arrival Time: ', datetime.fromtimestamp(
                    estimated_arrival_time_unix))
            estimated_buffer = estimated_arrival_time_unix
        json = get_json(flight, headers)
        estimated_arrival_time_unix = json['time']['estimated']['arrival']
        time.sleep(30)

    real_arrival_time_unix = json['time']['real']['arrival']
    if real_arrival_time_unix:
        print('Flight landed! Real Arrival Time: ',
              datetime.fromtimestamp(real_arrival_time_unix))


flight = '2e59e7d1'

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Cookie': 'showAds=yes; OptanonConsent=isIABGlobal=false&datestamp=Sun+Nov+27+2022+19%3A17%3A05+GMT%2B0300+(Moscow+Standard+Time)&version=202210.1.0&hosts=&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&geolocation=RU%3BSPE&AwaitingReconsent=false; OptanonAlertBoxClosed=2022-11-27T16:17:05.,131Z; __cfruid=52b8df4dc84fc6a2a7c1375b3c7a723ff9dfcd79-1669047322;',
    'DNT': '1',
    'Host': 'data-live.flightradar24.com',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'TE': 'trailers',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0'
}
