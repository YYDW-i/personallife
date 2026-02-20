import importlib
import re

from django.conf import settings
from news.models import NewsItem


_SENT_SPLIT = re.compile(r"(?<=[。！？!?\.])\s+")


def fallback_summary(text: str, lang: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    # 粗暴但稳定：取前 2~4 句，避免太长
    sents = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    picked = sents[:4]
    if len(picked) < 2 and len(sents) >= 2:
        picked = sents[:2]
    out = " ".join(picked)
    return out[:520]


def callable_summary(text: str, lang: str) -> str:
    """
    你把 settings.NEWS_SUMMARY_CALLABLE 指向一个函数：
    def get_news_brief(text: str, lang: str) -> str
    """
    path = getattr(settings, "NEWS_SUMMARY_CALLABLE", "")
    if not path or "." not in path:
        return fallback_summary(text, lang)

    mod_name, fn_name = path.rsplit(".", 1)
    mod = importlib.import_module(mod_name)
    fn = getattr(mod, fn_name)
    return (fn(text, lang) or "").strip()


def summarize_item(item: NewsItem, lang: str) -> str:
    lang = (lang or "zh").strip()

    # cache
    cached = (item.ai_summaries or {}).get(lang)
    if cached:
        return cached

    base_text = item.content_text or item.rss_summary or item.title
    backend = getattr(settings, "NEWS_SUMMARY_BACKEND", "fallback")

    if backend == "callable":
        summary = callable_summary(base_text, lang)
    else:
        summary = fallback_summary(base_text, lang)

    if not summary:
        summary = fallback_summary(item.rss_summary or item.title, lang)

    item.ai_summaries = {**(item.ai_summaries or {}), lang: summary}
    item.save(update_fields=["ai_summaries"])
    return summary