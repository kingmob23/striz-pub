import requests
import random


def get_free_proxies_list():
    r = requests.get(
        'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt')
    proxies_list = r.text.split()
    random.shuffle(proxies_list)
    return proxies_list


def get_webshare_proxies_list():
    r = requests.get(
        'https://proxy.webshare.io/api/v2/proxy/list/download/wegqngeehzhajwokecmujqmtbvbwzbqmaehgmbjl/-/any/username/direct/-/')
    proxies_list = r.text.split()
    return proxies_list


def make_get_request_with_proxie(url, proxies_list, headers):
    for i in proxies_list:

        formated = i.split(':')
        http = f'http://{formated[2]}:{formated[3]}@{formated[0]}:{formated[1]}'
        https = f'http://{formated[2]}:{formated[3]}@{formated[0]}:{formated[1]}'
        proxies = {'http': http, 'https': https}

        try:
            r = requests.get(url=url, proxies=proxies,
                             headers=headers, timeout=15)
            if r.status_code == 200:
                return r
        except requests.exceptions.ProxyError as e:
            continue
