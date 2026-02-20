from django.core.management.base import BaseCommand
from news.models import Topic, NewsSource


TOPICS = [
    ("politics", "政治", 10),
    ("tech", "科技", 20),
    ("finance", "财经", 30),
    ("sports", "体育", 40),
    ("entertainment", "娱乐", 50),
    ("culture", "文化", 60),
    ("ecology", "生态", 70),
    ("world", "国际", 80),
]

SOURCES = [
    # 中国：新华网 RSS（示例）
    ("新华网-时政", "http://www.xinhuanet.com/politics/news_politics.xml", "zh", "CN", ["politics"]),
    ("新华网-国际", "http://www.xinhuanet.com/world/news_world.xml", "zh", "CN", ["world"]),
    ("新华网-财经", "http://www.xinhuanet.com/finance/news_finance.xml", "zh", "CN", ["finance"]),
    ("新华网-科技", "http://www.xinhuanet.com/tech/news_tech.xml", "zh", "CN", ["tech"]),
    ("新华网-体育", "http://www.xinhuanet.com/sports/news_sports.xml", "zh", "CN", ["sports"]),
    ("新华网-娱乐", "http://www.xinhuanet.com/ent/news_ent.xml", "zh", "CN", ["entertainment"]),

    # 国际：BBC RSS（示例）
    ("BBC-Technology", "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/technology/rss.xml", "en", "UK", ["tech"]),
    ("BBC-Business", "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/business/rss.xml", "en", "UK", ["finance"]),
    ("BBC-Politics", "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/uk_politics/rss.xml", "en", "UK", ["politics"]),
]

class Command(BaseCommand):
    help = "Seed default topics and high-quality RSS sources for news app."

    def handle(self, *args, **options):
        topic_map = {}
        for slug, name, order in TOPICS:
            t, _ = Topic.objects.get_or_create(slug=slug, defaults={"name": name, "order": order})
            if t.name != name or t.order != order:
                t.name, t.order = name, order
                t.save(update_fields=["name", "order"])
            topic_map[slug] = t

        created = 0
        for name, rss_url, lang, region, topic_slugs in SOURCES:
            src, was_created = NewsSource.objects.get_or_create(
                rss_url=rss_url,
                defaults={"name": name, "language": lang, "region": region, "is_active": True, "weight": 1.0},
            )
            if not was_created:
                # 允许你改名/语言/地区后再跑也会同步
                src.name = name
                src.language = lang
                src.region = region
                src.save(update_fields=["name", "language", "region"])

            src.topics.set([topic_map[s] for s in topic_slugs if s in topic_map])
            created += 1 if was_created else 0

        self.stdout.write(self.style.SUCCESS(f"OK. Topics={Topic.objects.count()}, Sources={NewsSource.objects.count()} (new {created})"))