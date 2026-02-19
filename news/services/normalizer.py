from django.utils import timezone
from datetime import datetime

def normalize_rss_entry(e, source):
    return {
        "item_type": "NEWS",
        "source": source,
        "title": (getattr(e, "title", "") or "").strip()[:400],
        "summary": (getattr(e, "summary", "") or "").strip(),
        "url": getattr(e, "link", ""),
        "published_at": _guess_dt(getattr(e, "published_parsed", None)),
        "language": source.language,
        "region": source.region,
        "authors": [],
        "venue": source.name,
        "year": None,
        "doi": "",
        "raw": {},
    }

def normalize_arxiv_entry(e):
    # arXiv Atom entry 的字段你可以继续细化（authors、doi、primary_category 等）
    return {
        "item_type": "PAPER",
        "source": None,  # arXiv 可建成一个 Source(API)
        "title": (getattr(e, "title", "") or "").strip()[:400],
        "summary": (getattr(e, "summary", "") or "").strip(),
        "url": getattr(e, "link", ""),
        "published_at": _guess_dt(getattr(e, "published_parsed", None)),
        "language": "en",
        "region": "",
        "authors": [a.name for a in getattr(e, "authors", [])] if getattr(e, "authors", None) else [],
        "venue": "arXiv",
        "year": None,
        "doi": "",
        "raw": {},
    }

def _guess_dt(struct_time):
    if not struct_time:
        return timezone.now()
    dt = datetime(*struct_time[:6])
    return timezone.make_aware(dt, timezone.get_current_timezone())
