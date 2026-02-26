import json
import time
import socket
import os
import urllib.request
from typing import Any, Dict, Optional
from openai import OpenAI
from config import settings
from urllib.error import HTTPError, URLError

ZHIPU_API_KEY = settings.OPENAI_API_KEY  # 从环境变量读取智谱 API Key :contentReference[oaicite:3]{index=3}
ZHIPU_MODEL = settings.ZAI_MODEL  # 你也可以改成 glm-5 等:contentReference[oaicite:4]{index=4}
ZHIPU_BASE = settings.ZAI_BASE_URL


def _post_json(url: str, payload: dict, timeout: int = 120, retries: int = 3) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    print(f"发起请求: url={url}, retries={retries}")

    for attempt in range(retries):
        print(f"尝试 {attempt+1}/{retries}")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {ZHIPU_API_KEY}")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
            print(f"请求成功，状态码: {resp.status}")
            return json.loads(raw)

        except HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            print(f"HTTPError: {e.code}, body: {body}")
            raise RuntimeError(f"HTTP {e.code}: {body}")

        except (socket.timeout, TimeoutError, URLError) as e:
            # 最后一次仍失败就抛出
            print(f"网络异常: {e}")
            if attempt == retries - 1:
                raise RuntimeError(f"请求超时/网络异常：{e}")
            # 退避：1s, 2s, 4s...
            time.sleep(2 ** attempt)
        except Exception as e:
            print(f"其他异常: {e}")
            if attempt == retries - 1:
                raise RuntimeError(f"请求失败: {e}")
            time.sleep(2 ** attempt)


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
    # 提取本卦卦辞和爻辞
    primary_scripture = primary.get("scripture", "")
    primary_lines = primary.get("lines", [])  # 列表，每项包含 name, scripture, type

    # 提取之卦卦辞和爻辞（如果有）
    relating_scripture = relating.get("scripture", "") if relating else None
    relating_lines = relating.get("lines", []) if relating else None

    # 构造动爻信息：本卦动爻爻辞 + 之卦对应动爻爻辞
    moving_info = []
    for idx in moving_lines:
        line_idx = idx - 1  # 列表索引从0开始
        if line_idx < len(primary_lines):
            primary_line = primary_lines[line_idx]
            moving_info.append({
                "position": primary_line["name"],
                "original": primary_line["scripture"],
                "type": "本卦动爻"
            })
        if relating_lines and line_idx < len(relating_lines):
            relating_line = relating_lines[line_idx]
            moving_info.append({
                "position": relating_line["name"],
                "original": relating_line["scripture"],
                "type": "之卦动爻"
            })

    # 构造发送给 AI 的用户数据结构

    sys = (
        "你是一个以《周易》为文化背景的解读助手。"
        "严禁输出任何暴力/自残/违法/露骨/仇恨内容；"
        "不要逐字翻译或复述爻辞；只给抽象、温和、可执行的生活建议。"
        "如果用户填写了问题（question 字段），必须在最后一条建议中给出用户问题的答案**"
        "你必须只输出一个 JSON 对象，不得输出任何解释性文字、不得输出 Markdown、不得用 ```json 包裹。"
    )

    user = {
        "question": question or "（用户未填写问题）",
        "primary": {
            "name": primary.get("name"),
            "symbol": primary.get("symbol"),
            "scripture": primary.get("scripture"),
            "all_lines": [{"name": l["name"], "text": l["scripture"]} for l in primary_lines],
        },
        "relating": None if not relating else {
            "name": relating.get("name"),
            "symbol": relating.get("symbol"),
            "scripture": relating.get("scripture"),
            "all_lines": [{"name": l["name"], "text": l["scripture"]} for l in relating_lines],
        },
        "moving_lines": moving_lines,
        "moving_details": moving_info, 
        "requirements": [
            "请翻译以下内容：本卦卦辞、本卦动爻爻辞、之卦卦辞、之卦动爻爻辞（如果有）。",
            "翻译要简洁现代，保留原意。",
            "结合本卦和之卦的整体象征，给出 3-6 条可执行的行动建议，与用户问题相关。",
            "列举 1-2 个与卦象相关的历史典故（每条含 title, content, source 可空，如果有之卦也要加上之卦的典故）。",
            "最后加一句免责声明。",
            "避免任何暴力、自残、违法、露骨内容。"
            "如果用户填写了问题（question 字段），必须在提完建议后给出用户问题的答案**"
        ],
        "schema": {
            "translation": "一段综合译文，包含本卦卦辞、本卦动爻爻辞、之卦卦辞、之卦动爻爻辞的现代汉语翻译。",
            "interpretation": "结合用户问题的 3-6 条建议（列表）",
            "anecdotes": "与卦象相关的典故（列表，每条含 title, content, source 可空）",
            "disclaimer": "一句免责声明"
        }
    }

    payload = {
        "model": os.getenv("ZHIPU_MODEL", "glm-4"),   # 用支持结构化输出的模型
        "messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        "temperature": 0.5,
        "response_format": {"type": "json_object"},     # 关键：JSON 模式
        "stream": False,
        "max_tokens": 2048,
        "reasoning_method": "none"
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
        result = _safe_json_parse(content)
        return result
    except Exception as e:
        return {"error": f"AI 解读失败：{e}"}