import asyncio
import aiohttp
from dotenv import load_dotenv
import os


load_dotenv()
ua_apikey = os.environ['UAAPIKEY']
proxy_auth = os.environ['PROXY']


async def user_agent():
    async with aiohttp.ClientSession() as session:
        async with session.get(url="https://api.apilayer.com/user_agent/generate?windows=windows&tablet=tablet&mobile=mobile&mac=mac&linux=linux&ie=ie&firefox=firefox&desktop=desktop&chrome=chrome&android=android", headers={"apikey": ua_apikey}) as r:
            result = await r.json()
            ua = result['ua']
            headers = {
                'User-Agent': ua
            }
            return headers


async def get_proxy():
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://proxy.webshare.io/api/v2/proxy/list/download/{proxy_auth}/-/any/username/direct/-/') as r:
            raw_proxy = await r.text()
            proxy_list = raw_proxy.split()
            return proxy_list


async def make_requset(url, content):
    async with aiohttp.ClientSession() as session:
        proxy_list = await asyncio.create_task(get_proxy())
        for i in proxy_list:
            parts = i.split(':')
            proxy = f'http://{parts[0]}:{parts[1]}'
            proxy_auth = aiohttp.BasicAuth(f'{parts[2]}', f'{parts[3]}')
            headers = await asyncio.create_task(user_agent())
            async with session.get(url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth) as r:
                if r.status == 200:
                    if content == 'json':
                        return await r.json()
                    elif content == 'text':
                        return await r.text()
                else:
                    continue
