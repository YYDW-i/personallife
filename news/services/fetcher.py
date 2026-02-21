import feedparser
import trafilatura
from datetime import datetime, timezone as dt_tz

from django.db import transaction
from django.utils import timezone

from news.models import NewsSource, NewsItem


def _parse_dt(entry):
    # feedparser 用 struct_time
    st = entry.get("published_parsed") or entry.get("updated_parsed")
    if not st:
        return None
    # 当作 UTC 处理，再转为 Django 当前时区
    dt = datetime(*st[:6], tzinfo=dt_tz.utc)
    return dt.astimezone(timezone.get_current_timezone())


def _extract_text(url: str) -> str:
    try:
        downloaded = trafilatura.fetch_url(url, timeout=10)
        if not downloaded:
            return ""
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        return text or ""
    except Exception:
        return ""


@transaction.atomic
def fetch_source(source: NewsSource, max_entries: int = 50) -> int:
    parsed = feedparser.parse(source.rss_url)
    if getattr(parsed, "bozo", False):
        # 解析失败就跳过
        return 0

    new_count = 0
    for entry in (parsed.entries or [])[:max_entries]:
        link = entry.get("link") or ""
        title = (entry.get("title") or "").strip()
        guid = (entry.get("id") or entry.get("guid") or link or title)[:500]

        if not link or not title:
            continue

        published_at = _parse_dt(entry)
        summary = (entry.get("summary") or entry.get("description") or "").strip()
        item_type = getattr(source, "type", "RSS")
        obj, created = NewsItem.objects.get_or_create(
            source=source,
            guid=guid,
            defaults={
                "title": title[:500],
                "link": link[:1000],
                "published_at": published_at,
                "rss_summary": summary,
                "item_type": item_type,
            },
        )
        if created:
            new_count += 1
            # 只对新条目抓正文（抓不到也无所谓）
            text = _extract_text(link)
            if text:
                obj.content_text = text
                obj.save(update_fields=["content_text"])

    return new_count


def fetch_all_sources() -> int:
    total_new = 0
    for src in NewsSource.objects.filter(is_active=True):
        total_new += fetch_source(src)
    return total_new