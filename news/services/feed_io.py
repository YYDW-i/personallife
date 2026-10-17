"""有超时和大小限制的 RSS 下载；数据库写入留在调用线程。"""
import requests


def download_feed(url):
    with requests.get(url, timeout=(5, 15), stream=True,
                      headers={"User-Agent": "LocalLife/2.0 RSS Reader"}) as response:
        response.raise_for_status()
        chunks = []
        size = 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > 5 * 1024 * 1024:
                raise ValueError("RSS 内容超过 5 MB")
            chunks.append(chunk)
        return b"".join(chunks)
