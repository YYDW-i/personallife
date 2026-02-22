from django.core.management.base import BaseCommand
from news.models import Topic, NewsSource

TOPICS = [
    ("politics", "政治", 10),
    ("tech", "科技", 20),
    ("entertainment", "娱乐", 50),
    ("culture", "文化", 60),
    ("ecology", "生态", 70),
    ("finance", "财经", 30),
    ("sports", "体育", 40),
    ("world", "国际", 80),
]

SOURCES = [
    ("新华网-时政", "http://www.xinhuanet.com/politics/news_politics.xml", "zh", "CN", ["politics"]),
    ("新华网-国际", "http://www.xinhuanet.com/world/news_world.xml", "zh", "CN", ["world"]),
    ("新华网-财经", "http://www.xinhuanet.com/finance/news_finance.xml", "zh", "CN", ["finance"]),
    ("新华网-科技", "http://www.xinhuanet.com/tech/news_tech.xml", "zh", "CN", ["tech"]),
    ("新华网-体育", "http://www.xinhuanet.com/sports/news_sports.xml", "zh", "CN", ["sports"]),
    ("新华网-娱乐", "http://www.xinhuanet.com/ent/news_ent.xml", "zh", "CN", ["entertainment"]),

    ("BBC-Technology", "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/technology/rss.xml", "en", "INTER", ["tech"]),
    ("BBC-Business", "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/business/rss.xml", "en", "INTER", ["finance"]),
    ("BBC-Politics", "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/uk_politics/rss.xml", "en", "INTER", ["politics"]),
    ("BBC-World", "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/world/rss.xml", "en", "INTER", ["world"]),
    ("BBC-Entertainment", "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/entertainment/rss.xml", "en", "INTER", ["ecology"]),

]

class Command(BaseCommand):
    help = "Seed default topics and RSS sources."

    def handle(self, *args, **options):
        topic_map = {}
        for slug, name, order in TOPICS:
            t, _ = Topic.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "order": order},
            )
            topic_map[slug] = t

        for name, rss_url, lang, region, topic_slugs in SOURCES:
            src, _ = NewsSource.objects.update_or_create(
                rss_url=rss_url,
                defaults={
                    "name": name,
                    "language": lang,
                    "region": region,
                    "is_active": True,
                    "weight": 1.0,
                },
            )
            src.topics.set([topic_map[s] for s in topic_slugs if s in topic_map])

        self.stdout.write(self.style.SUCCESS("OK: topics & sources seeded."))