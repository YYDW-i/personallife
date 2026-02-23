from django.core.management.base import BaseCommand
from analytics_app.iching_data import ensure_dataset_ready

class Command(BaseCommand):
    help = "Download and cache iching.json into analytics_app/data/iching.json"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Force re-download")

    def handle(self, *args, **options):
        force = options.get("force", False)
        ensure_dataset_ready(force_download=force)
        self.stdout.write(self.style.SUCCESS("iching.json 已就绪（已缓存到 analytics_app/data/iching.json）"))