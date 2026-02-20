from django.core.management.base import BaseCommand
from django.utils import timezone

from news.services.fetcher import fetch_all_sources
from news.services.brief import build_briefs_for_all_users


class Command(BaseCommand):
    help = "Fetch RSS sources and build daily briefs for all users."

    def handle(self, *args, **options):
        new_count = fetch_all_sources()
        brief_count = build_briefs_for_all_users(date=timezone.localdate())
        self.stdout.write(self.style.SUCCESS(f"OK. NewItems={new_count}, BriefsBuilt={brief_count}"))