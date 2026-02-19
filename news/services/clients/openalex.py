# news/services/clients/openalex.py
from django.conf import settings
from ..http import make_session, RateLimiter
from ..normalizer import normalize_openalex_work
from ..dedup import url_normalize, make_content_hash

def fetch_openalex(search: str, per_page=25):
    s = make_session()
    limiter = RateLimiter(1.0)
    params = {"search": search, "per_page": per_page}
    headers = {}
    if getattr(settings, "OPENALEX_API_KEY", ""):
        headers["Authorization"] = f"Bearer {settings.OPENALEX_API_KEY}"
        params["api_key"] = getattr(settings, "OPENALEX_API_KEY", "")

    limiter.wait()
    r = s.get("https://api.openalex.org/works", params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    items = []
    for w in data.get("results", []):
        norm = normalize_openalex_work(w)
        norm["normalized_url"] = url_normalize(norm["url"])
        norm["content_hash"] = make_content_hash(norm)
        items.append(norm)
    return items
