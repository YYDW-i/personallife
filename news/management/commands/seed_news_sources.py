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
    ("中新网-时政", "https://www.chinanews.com.cn/rss/china.xml", "zh", "CN", ["politics"]),
    ("中新网-国际", "https://www.chinanews.com.cn/rss/world.xml", "zh", "CN", ["world"]),
    ("中新网-财经", "https://www.chinanews.com.cn/rss/finance.xml", "zh", "CN", ["finance"]),
    ("中新网-科技", "https://www.chinanews.com.cn/rss/society.xml", "zh", "CN", ["tech"]),
    ("中新网-体育", "https://www.chinanews.com.cn/rss/sports.xml", "zh", "CN", ["sports"]),
    ("中新网-娱乐", "https://www.chinanews.com.cn/rss/culture.xml", "zh", "CN", ["entertainment"]),

    ("BBC-Technology", "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/technology/rss.xml", "en", "INTER", ["tech"]),
    ("BBC-Business", "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/business/rss.xml", "en", "INTER", ["finance"]),
    ("BBC-Politics", "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/uk_politics/rss.xml", "en", "INTER", ["politics"]),
    ("BBC-World", "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/world/rss.xml", "en", "INTER", ["world"]),
    ("BBC-Entertainment", "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/entertainment/rss.xml", "en", "INTER", ["entertainment"]),
    ("BBC-Sport", "https://feeds.bbci.co.uk/sport/rss.xml", "en", "INTER", ["sports"]),


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
        
        current_urls = [src[1] for src in SOURCES]
        # 将数据库中不在此列表中的源设为非活跃
        NewsSource.objects.exclude(rss_url__in=current_urls).update(is_active=False)
        self.stdout.write(self.style.SUCCESS("OK: topics & sources seeded."))