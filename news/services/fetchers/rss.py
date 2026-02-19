import feedparser
from django.utils import timezone
from ..normalizer import normalize_rss_entry
from ..dedup import url_normalize, make_content_hash

def fetch_rss(source, limiter=None):
    if limiter:
        limiter.wait()

    # feedparser 支持 etag / modified 做 conditional GET（304 不改就不重复入库）
    d = feedparser.parse(source.url_or_endpoint, etag=source.etag or None, modified=source.last_modified or None)

    # 更新增量字段
    if getattr(d, "etag", None):
        source.etag = d.etag
    if getattr(d, "modified", None):
        source.last_modified = str(d.modified)
    source.last_fetched_at = timezone.now()
    source.save(update_fields=["etag", "last_modified", "last_fetched_at"])

    items = []
    for e in getattr(d, "entries", []):
        norm = normalize_rss_entry(e, source=source)
        norm["normalized_url"] = url_normalize(norm["url"])
        norm["content_hash"] = make_content_hash(norm)
        items.append(norm)

    return items
