import json
import os
import urllib.request
from typing import Any, Dict, Optional
from openai import OpenAI
from config import settings
from urllib.error import HTTPError, URLError

ZHIPU_API_KEY = settings.OPENAI_API_KEY  # 从环境变量读取智谱 API Key :contentReference[oaicite:3]{index=3}
ZHIPU_MODEL = settings.ZAI_MODEL  # 你也可以改成 glm-5 等:contentReference[oaicite:4]{index=4}
ZHIPU_BASE = settings.ZAI_BASE_URL


def _post_json(url: str, payload: dict, timeout: int = 30) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {ZHIPU_API_KEY}")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)

    except HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code}: {body}")

    except URLError as e:
        raise RuntimeError(f"Network error: {e}")


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
        "严禁输出任何暴力/自残/违法/露骨/仇恨内容；"
        "不要逐字翻译或复述爻辞；只给抽象、温和、可执行的生活建议。"
        "你必须只输出一个 JSON 对象，不得输出任何解释性文字、不得输出 Markdown、不得用 ```json 包裹。"
    )

    user = {
        "question": question or "（用户未填写问题）",
        "primary": {
            "name": primary.get("name"),
            "symbol": primary.get("symbol"),
            "scripture": primary.get("scripture"),
        },
        "relating": None if not relating else {
            "name": relating.get("name"),
            "symbol": relating.get("symbol"),
            "scripture": relating.get("scripture"),
        },
        "moving_lines": moving_lines,
        "requirements": [
            "不要逐字复述或改写爻辞原文",
            "用文化/象征角度给出反思与行动建议",
            "避免任何暴力、自残、违法、露骨等内容"
        ],
        "schema": {
            "translation": "把卦辞+动爻爻辞翻成现代汉语（简洁）",
            "interpretation": "结合用户问题给出 3-6 条可执行建议（列表）",
            "anecdotes": "相关典故（列表，每条含 title, content, source 可空）",
            "disclaimer": "一句免责声明"
        }
    }

    payload = {
        "model": os.getenv("ZHIPU_MODEL", "glm-4.7"),   # 用支持结构化输出的模型
        "messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"},     # 关键：JSON 模式
        "stream": False
    }

    try:
        data = _post_json(f"{ZHIPU_BASE}/chat/completions", payload, timeout=45)
        content = data["choices"][0]["message"]["content"]
        # 强制解析 JSON
        def _safe_json_parse(content: str) -> dict:
            if not content or not content.strip():
                raise RuntimeError("AI 返回内容为空（可能被拦截/截断），无法解析 JSON")

            s = content.strip()

            # 直接尝试
            try:
                return json.loads(s)
            except Exception:
                pass

            # 尝试从文本中抠出最外层 { ... }
            l = s.find("{")
            r = s.rfind("}")
            if l != -1 and r != -1 and r > l:
                try:
                    return json.loads(s[l:r+1])
                except Exception:
                    pass

            # 实在不行，把原文截断抛出来，便于你在页面上看到它到底回了啥
            raise RuntimeError(f"AI 未返回合法 JSON，原始内容前200字：{s[:200]!r}")
    except Exception as e:
        return {"error": f"AI 解读失败：{e}"}