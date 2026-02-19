import time
import requests
import requests_cache

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 可选：启用持久缓存（SQLite 文件）
requests_cache.install_cache("news_http_cache", expire_after=600)  # 10分钟

def make_session(user_agent: str = "LocalLifeNewsBot/0.1"):
    s = requests.Session()
    s.headers.update({"User-Agent": user_agent})

    retry = Retry(
        total=3,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s

class RateLimiter:
    def __init__(self, min_interval=1.0):
        self.min_interval = min_interval
        self._last = 0.0

    def wait(self):
        now = time.time()
        delta = now - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last = time.time()
