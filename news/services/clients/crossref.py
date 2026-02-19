# news/services/clients/crossref.py
from ..http import make_session, RateLimiter
from ..normalizer import normalize_crossref_work
from ..dedup import url_normalize, make_content_hash

def fetch_crossref(query: str, from_pub_date: str, rows=25):
    s = make_session()
    limiter = RateLimiter(1.0)

    params = {
        "query": query,
        "rows": rows,
        "filter": f"from-pub-date:{from_pub_date}",
        "sort": "published",
        "order": "desc",
    }
    limiter.wait()
    r = s.get("https://api.crossref.org/works", params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    items = []
    for w in data.get("message", {}).get("items", []):
        norm = normalize_crossref_work(w)
        norm["normalized_url"] = url_normalize(norm["url"])
        norm["content_hash"] = make_content_hash(norm)
        items.append(norm)
    return items
