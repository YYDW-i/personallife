from django.core.management.base import BaseCommand
from django.utils import timezone

from news.models import Source, UserPreference, Item
from news.services.fetchers.rss import fetch_rss
from news.services import upsert_items
from news.services.http import RateLimiter
from news.services.digest_builder import build_digest_for_user

class Command(BaseCommand):
    help = "Run news pipeline: fetch -> store -> generate digests"

    def handle(self, *args, **opts):
        limiter = RateLimiter(min_interval=1.0)

        # 1) fetch RSS sources
        all_norm = []
        for src in Source.objects.filter(enabled=True, type="RSS"):
            try:
                items = fetch_rss(src, limiter=limiter)
                all_norm.extend(items)
            except Exception as e:
                self.stderr.write(f"[RSS] {src.name} failed: {e}")

        created = upsert_items(all_norm)
        self.stdout.write(f"items created: {created}")

        # 2) generate digests for users (for today; 实际用“到点用户”版本）
        today = timezone.localdate()
        ranking_params = {
            "freshness_window_hours": 48,
            "w_freshness": 1.0,
            "w_source": 0.6,
            "w_match": 1.2,
        }

        for pref in UserPreference.objects.select_related("user"):
            # 简单候选：最近 48h
            since = timezone.now() - timezone.timedelta(hours=48)
            qs = Item.objects.filter(published_at__gte=since).select_related("source")
            digest = build_digest_for_user(pref.user, today, pref, qs, ranking_params)
            pref.last_digest_date = today
            pref.save(update_fields=["last_digest_date"])
            self.stdout.write(f"digest generated: {pref.user} {digest.id}")
