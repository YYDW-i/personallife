import hashlib
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

TRACKING_PARAMS_PREFIX = ("utm_",)
DROP_PARAMS = {"spm", "from", "source"}

def url_normalize(url: str) -> str:
    parts = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
         if not k.startswith(TRACKING_PARAMS_PREFIX) and k not in DROP_PARAMS]
    q.sort()
    clean = parts._replace(fragment="", query=urlencode(q, doseq=True))
    return urlunsplit(clean)

def make_content_hash(norm: dict) -> str:
    base = f"{norm.get('title','')}|{norm.get('summary','')}|{norm.get('published_at','')}|{norm.get('url','')}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
