from django.conf import settings
from django.db import models


class Topic(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=32)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.name


class NewsSource(models.Model):
    class SourceType(models.TextChoices):
        RSS = "RSS", "RSS/Atom"
        API = "API", "Official API"

    # 关键：把 type 加回来，给默认值，避免以后再插入失败
    type = models.CharField(
        max_length=8,
        choices=SourceType.choices,
        default=SourceType.RSS,
    )
    name = models.CharField(max_length=1200)
    rss_url = models.URLField(unique=True)
    language = models.CharField(max_length=100, default="zh")   # zh / en / ...
    region = models.CharField(max_length=100, blank=True, default="CN")  # CN / US / ...
    topics = models.ManyToManyField(Topic, blank=True, related_name="sources")
    is_active = models.BooleanField(default=True)
    weight = models.FloatField(default=1.0)

    def __str__(self) -> str:
        return self.name


class NewsItem(models.Model):
    source = models.ForeignKey(NewsSource, on_delete=models.CASCADE, related_name="items")
    guid = models.CharField(max_length=500)  # RSS 的 id/guid/链接兜底
    title = models.CharField(max_length=500)
    link = models.URLField(max_length=1000)
    published_at = models.DateTimeField(null=True, blank=True)

    # 设置默认值，避免 NULL 约束错误
    summary = models.TextField(blank=True, default="")  # 设置空字符串作为默认值

    item_type = models.CharField(
        max_length=8,
        choices=NewsSource.SourceType.choices,
        default=NewsSource.SourceType.RSS,
    )

    rss_summary = models.TextField(blank=True, default="")
    content_text = models.TextField(blank=True, default="")

    fetched_at = models.DateTimeField(auto_now_add=True)

    # {"zh": "…2-4句…", "en": "…"}
    ai_summaries = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("source", "guid")]
        indexes = [
            models.Index(fields=["published_at"]),
            models.Index(fields=["fetched_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.source.name}: {self.title[:40]}"


class UserNewsPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="news_pref")
    enabled = models.BooleanField(default=True)
    include_keywords = models.CharField(max_length=255, default='')  # 设置默认值
    topics = models.ManyToManyField(Topic, blank=True,default="")
    language = models.CharField(max_length=10, default="zh")
    region = models.CharField(max_length=10, blank=True, default="")

    # 逗号分隔关键词：AI, 芯片, OpenAI
    keywords = models.CharField(max_length=300, blank=True, default="")

    max_items = models.PositiveSmallIntegerField(default=8)

    def keyword_list(self):
        return [k.strip() for k in self.keywords.split(",") if k.strip()]

    def __str__(self) -> str:
        return f"Pref({self.user})"


class DailyBrief(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="news_briefs")
    date = models.DateField()
    language = models.CharField(max_length=10, default="zh")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "date", "language")]
        ordering = ["-date", "-id"]

    def __str__(self) -> str:
        return f"{self.user} {self.date} ({self.language})"


class BriefEntry(models.Model):
    brief = models.ForeignKey(DailyBrief, on_delete=models.CASCADE, related_name="entries")
    item = models.ForeignKey(NewsItem, on_delete=models.CASCADE)

    title = models.CharField(max_length=500)
    summary = models.TextField()
    url = models.URLField(max_length=1000)
    source_name = models.CharField(max_length=120)

    score = models.FloatField(default=0)

    class Meta:
        ordering = ["-score", "-item__published_at", "-id"]