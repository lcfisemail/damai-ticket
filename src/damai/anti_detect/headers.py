"""请求头轮换池"""
import random
from typing import Optional

# 真实浏览器 User-Agent 池
_USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    # Chrome on Android (移动端)
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
]

_DAMAI_REFERERS = [
    "https://m.damai.cn/",
    "https://m.damai.cn/damai/home/index.html",
    "https://m.damai.cn/damai/search/index.html",
]

_ACCEPT_LANGUAGES = [
    "zh-CN,zh;q=0.9,en;q=0.8",
    "zh-CN,zh;q=0.9",
    "zh-CN,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6",
    "zh,zh-CN;q=0.9,en;q=0.8",
]


def get_random_ua() -> str:
    return random.choice(_USER_AGENTS)


def get_random_referer() -> str:
    return random.choice(_DAMAI_REFERERS)


def build_headers(
    ua: Optional[str] = None,
    referer: Optional[str] = None,
    extra: Optional[dict] = None,
) -> dict[str, str]:
    """构建完整请求头"""
    headers = {
        "User-Agent": ua or get_random_ua(),
        "Accept": "application/json",
        "Accept-Language": random.choice(_ACCEPT_LANGUAGES),
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://m.damai.cn",
        "Referer": referer or get_random_referer(),
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
    }
    if extra:
        headers.update(extra)
    return headers
