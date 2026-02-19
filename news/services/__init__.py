from django.db import transaction
from django.utils import timezone
from news.models import Item

def upsert_items(normalized_items):
    created = 0
    with transaction.atomic():
        for n in normalized_items:
            obj, is_new = Item.objects.get_or_create(
                normalized_url=n["normalized_url"],
                defaults={
                    "item_type": n["item_type"],
                    "source": n["source"],
                    "title": n["title"],
                    "summary": n["summary"][:4000],
                    "url": n["url"],
                    "published_at": n["published_at"],
                    "language": n.get("language",""),
                    "region": n.get("region",""),
                    "authors": n.get("authors", []),
                    "venue": n.get("venue",""),
                    "year": n.get("year"),
                    "doi": n.get("doi",""),
                    "content_hash": n["content_hash"],
                    "raw": n.get("raw", {}),
                }
            )
            if is_new:
                created += 1
    return created
