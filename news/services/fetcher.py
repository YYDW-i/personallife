import feedparser
import trafilatura
import logging
from urllib.parse import urlsplit
from .feed_io import download_feed
from datetime import datetime, timezone as dt_tz

from django.db import transaction
from django.utils import timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def fetch_source(source: NewsSource, max_entries: int = 50) -> int:
    return _save_feed(source, download_feed(source.rss_url), max_entries)


def _save_feed(source, content, max_entries=50):
    parsed = feedparser.parse(content)
    if getattr(parsed, "bozo", False) and not parsed.entries:
        # 解析失败就跳过
        return 0

    new_count = 0
    for entry in (parsed.entries or [])[:max_entries]:
        link = entry.get("link") or ""
        title = (entry.get("title") or "").strip()
        guid = (entry.get("id") or entry.get("guid") or link or title)[:500]

        if not link or not title or urlsplit(link).scheme not in ("http", "https"):
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

    return new_count


def fetch_all_sources():
    sources = list(NewsSource.objects.filter(is_active=True))
    total = 0
    successful = 0
    # 并发下载，串行写 SQLite，避免多个线程在网络等待期间持有写锁。
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(download_feed, src.rss_url): src for src in sources}
        for future in as_completed(futures):
            source = futures[future]
            try:
                content = future.result()
                total += _save_feed(source, content)
                successful += 1
            except Exception:
                logging.getLogger(__name__).warning("新闻源同步失败：%s", source.name, exc_info=True)
    if sources and not successful:
        raise RuntimeError("所有新闻源均无法连接，请检查网络或新闻源设置。")
    return total
