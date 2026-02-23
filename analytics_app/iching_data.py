import json
import os
import urllib.request
from typing import Any, Dict, List, Tuple

# 自动下载源（结构化数据）
OPEN_ICHING_JSON_URL = "https://raw.githubusercontent.com/john-walks-slow/open-iching/main/iching/iching.json"

# 缓存到你项目的 analytics_app/data/iching.json
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
LOCAL_JSON_PATH = os.path.join(DATA_DIR, "iching.json")

_DATA: List[Dict[str, Any]] | None = None
_IDX: Dict[Tuple[int, ...], Dict[str, Any]] | None = None


def ensure_dataset_ready(force_download: bool = False) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    if (not force_download) and os.path.exists(LOCAL_JSON_PATH) and os.path.getsize(LOCAL_JSON_PATH) > 1000:
        return

    # 下载并保存
    try:
        with urllib.request.urlopen(OPEN_ICHING_JSON_URL, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
        with open(LOCAL_JSON_PATH, "w", encoding="utf-8") as f:
            f.write(raw)
    except Exception as e:
        raise RuntimeError(f"下载 iching.json 失败（可能无网络/被墙/超时）：{e}")


def _load() -> None:
    global _DATA, _IDX
    if _IDX is not None:
        return

    ensure_dataset_ready()

    with open(LOCAL_JSON_PATH, "r", encoding="utf-8") as f:
        _DATA = json.load(f)

    idx: Dict[Tuple[int, ...], Dict[str, Any]] = {}
    for item in _DATA:
        arr = tuple(item["array"])
        idx[arr] = item

    if len(idx) < 64:
        raise RuntimeError(f"iching.json 不完整：只加载到 {len(idx)} 卦")

    _IDX = idx


def get_hex_by_array(arr: List[int]) -> Dict[str, Any]:
    _load()
    key = tuple(arr)
    assert _IDX is not None
    if key not in _IDX:
        raise KeyError(f"未找到该卦：{arr}")
    return _IDX[key]