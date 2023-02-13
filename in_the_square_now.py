import requests
import random
import os

from proxie import get_webshare_proxies_list, make_get_request_with_proxie


domen2 = os.environ['DOMEN2']


def get_planes_in_the_square(latitude, longitude):
    square_url = f'https://{domen2}/zones/fcgi/feed.js?faa=1&bounds={latitude},{longitude},-0.352,10.172&satellite=1&mlat=1&flarm=1&adsb=1&gnd=1&air=1&vehicles=1&estimated=1&maxage=14400&gliders=1&stats=1'

    api_headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0',
    }

    proxies = get_webshare_proxies_list()

    r = make_get_request_with_proxie(
        url=square_url, proxies_list=proxies, headers=api_headers)
    json = r.json()
    return (json)


latitude = 53.189
longitude = 51.292
print(get_planes_in_the_square(latitude, longitude))
