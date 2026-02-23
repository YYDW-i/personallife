import json
import os
import urllib.request
from typing import Any, Dict, Optional
from openai import OpenAI
from config import settings

ZHIPU_API_KEY = settings.OPENAI_API_KEY  # 从环境变量读取智谱 API Key :contentReference[oaicite:3]{index=3}
ZHIPU_MODEL = settings.ZAI_MODEL  # 你也可以改成 glm-5 等:contentReference[oaicite:4]{index=4}
ZHIPU_BASE = settings.ZAI_BASE_URL


def _post_json(url: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {ZHIPU_API_KEY}")

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def zhipu_interpret_optional(
    question: str,
    primary: Dict[str, Any],
    relating: Optional[Dict[str, Any]],
    moving_lines: list[int],
) -> Optional[Dict[str, Any]]:
    if not ZHIPU_API_KEY:
        return {
            "error": "未配置 ZHIPU_API_KEY（环境变量）。已跳过 AI 解读。",
        }

    sys = (
        "你是一个以《周易》为文化背景的解读助手。"
        "请务必：1) 不做医疗/法律/财务的确定性断言；2) 语气偏“反思与行动建议”；"
        "3) 典故如果不确定来源，就写“暂无可核验来源”。"
        "输出必须是严格 JSON（不要 Markdown）。"
    )

    user = {
        "question": question or "（用户未填写问题）",
        "primary": {
            "name": primary.get("name"),
            "symbol": primary.get("symbol"),
            "scripture": primary.get("scripture"),
            "lines": primary.get("lines", []),
        },
        "relating": None if not relating else {
            "name": relating.get("name"),
            "symbol": relating.get("symbol"),
            "scripture": relating.get("scripture"),
        },
        "moving_lines": moving_lines,
        "schema": {
            "translation": "把卦辞+动爻爻辞翻成现代汉语（简洁）",
            "interpretation": "结合用户问题给出 3-6 条可执行建议（列表）",
            "anecdotes": "相关典故（列表，每条含 title, content, source 可空）",
            "disclaimer": "一句免责声明"
        }
    }

    payload = {
        "model": ZHIPU_MODEL,
        "messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        "temperature": 0.7,
    }

    try:
        data = _post_json(f"{ZHIPU_BASE}/chat/completions", payload, timeout=45)
        content = data["choices"][0]["message"]["content"]
        # 强制解析 JSON
        return json.loads(content)
    except Exception as e:
        return {"error": f"AI 解读失败：{e}"}