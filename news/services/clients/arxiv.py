# news/services/clients/arxiv.py
from django.utils import timezone
import feedparser
from ..normalizer import normalize_arxiv_entry
from ..dedup import url_normalize, make_content_hash

def fetch_arxiv(query: str, max_results=25):
    # arXiv API 返回 Atom XML（feedparser 可解析）
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    d = feedparser.parse(url)
    items = []
    for e in getattr(d, "entries", []):
        norm = normalize_arxiv_entry(e)
        norm["normalized_url"] = url_normalize(norm["url"])
        norm["content_hash"] = make_content_hash(norm)
        items.append(norm)
    return items
