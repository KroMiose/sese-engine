import time
import random
import logging
from functools import lru_cache
from urllib.parse import urlparse
from typing import Optional, Tuple, Iterable, Dict, List

# from reppy.robots import Robots, AllowNone
import requests

from 配置 import 爬虫的名字, 爬虫冷却时间, 上不上代理, 爬虫的代理服务器

logging.getLogger('urllib3.connection').setLevel(logging.CRITICAL)  # urllib3太吵了
logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)


class LoliError(Exception):
    ...


# @lru_cache(maxsize=512)
# def 萝卜(url):
#     rp = Robots.fetch(url+'/robots.txt', timeout=5, headers={'user-agent': 爬虫的名字})
#     if isinstance(rp, AllowNone):
#         rp = Robots.fetch(url+'/robots.txt', timeout=5)
#     return rp


def _解析文本(resp, 大小限制=None) -> str:
    if 大小限制:
        data = b''
        for b in resp.iter_content(4096):
            data += b
            if len(data) > 大小限制:
                break
    else:
        data = resp.content
    if resp.encoding == 'ISO-8859-1':   # 猜测编码的性能太差，直接硬上
        try:
            return data.decode('utf8')
        except Exception:
            try:
                return data.decode('gbk')
            except Exception:
                return data.decode('utf8', 'ignore')
    else:
        return data.decode(resp.encoding, 'ignore')


def _重定向表(resp) -> Iterable[Tuple[str, str]]:
    for i in resp.history:
        if i.status_code in (301, 308):
            yield i.url, i.headers['Location']


限流计时 = {}


def 真爬(url, 乖=True, timeout=5, 大小限制=None) -> Tuple[str, str, Dict[str, str], str]:
    global 限流计时
    q = urlparse(url)
    if 乖:
        now = time.time()
        if now - 限流计时.get(q.netloc, 0) < 爬虫冷却时间:
            time.sleep(爬虫冷却时间 * (0.5 + 0.5 * random.random()))
            return 真爬(url, 乖, timeout, 大小限制)
        限流计时[q.netloc] = now
        if random.random() < 0.01:
            限流计时 = {k: v for k, v in 限流计时.items() if now - v < 爬虫冷却时间 + 1}
    if 乖:
        pass # 不管，反正就是可以
        # rp = 萝卜(f'{q.scheme}://{q.netloc}')
        # if not rp.allowed(url, 爬虫的名字):
        #     raise LoliError('被禁了，不行！')
    resp = requests.get(url, timeout=timeout, headers={'user-agent': 爬虫的名字}, stream=True, proxies=爬虫的代理服务器 if 上不上代理 else None)
    if resp.status_code == 404:
        raise LoliError('没有！没有！')
    if 400 <= resp.status_code < 500:
        resp = requests.get(url, timeout=timeout/2, stream=True, proxies=爬虫的代理服务器 if 上不上代理 else None)
    resp.raise_for_status()
    if 'text/html' not in resp.headers.get('Content-Type', ''):
        raise LoliError(f'类型{resp.headers.get("Content-Type")}不行！')
    return _解析文本(resp, 大小限制), resp.url, dict(_重定向表(resp)), resp.headers.get('Server', '')


def 爬(url, **d) -> Optional[Tuple[str, str, Dict[str, str], str]]:
    try:
        return 真爬(url, **d)
    except LoliError as e:
        logging.info(f'{url} {e}')
        return None
