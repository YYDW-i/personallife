from django.conf import settings
from django.db import models
from django.utils import timezone

class Category(models.Model):
    slug = models.SlugField(unique=True)   # tech, politics...
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Source(models.Model):
    class SourceType(models.TextChoices):
        RSS = "RSS", "RSS/Atom"
        API = "API", "Official API"

    name = models.CharField(max_length=120)
    type = models.CharField(max_length=8, choices=SourceType.choices)
    url_or_endpoint = models.URLField()
    categories = models.ManyToManyField(Category, blank=True)

    language = models.CharField(max_length=16, blank=True)  # e.g. en, zh
    region = models.CharField(max_length=32, blank=True)    # e.g. UK, CN, Global
    weight = models.FloatField(default=1.0)
    enabled = models.BooleanField(default=True)

    # RSS 增量
    etag = models.CharField(max_length=200, blank=True)
    last_modified = models.CharField(max_length=200, blank=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    class ItemType(models.TextChoices):
        NEWS = "NEWS", "News"
        PAPER = "PAPER", "Paper"

    item_type = models.CharField(max_length=10, choices=ItemType.choices)
    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="items")

    title = models.CharField(max_length=400)
    summary = models.TextField(blank=True)  # “概述/摘要”，不放全文
    url = models.URLField()
    normalized_url = models.URLField(unique=True)

    published_at = models.DateTimeField(db_index=True)
    language = models.CharField(max_length=16, blank=True)
    region = models.CharField(max_length=32, blank=True)

    # 学术字段（可空）
    authors = models.JSONField(default=list, blank=True)
    venue = models.CharField(max_length=200, blank=True)  # journal / platform
    year = models.IntegerField(null=True, blank=True)
    doi = models.CharField(max_length=200, blank=True)

    content_hash = models.CharField(max_length=64, db_index=True)  # sha256
    raw = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["source", "published_at"]),
        ]

    def __str__(self):
        return f"[{self.item_type}] {self.title[:50]}"


class UserPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    categories = models.ManyToManyField(Category, blank=True)

    language = models.CharField(max_length=16, blank=True)  # ''=any
    region = models.CharField(max_length=32, blank=True)    # ''=any

    include_keywords = models.TextField(blank=True)  # 逗号/换行分隔
    exclude_keywords = models.TextField(blank=True)

    daily_limit = models.IntegerField(default=20)
    push_time = models.TimeField(default=timezone.datetime(2000,1,1,8,0).time())

    include_academic = models.BooleanField(default=False)
    last_digest_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Pref({self.user})"


class Digest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "date")]
        indexes = [models.Index(fields=["user", "date"])]

    def __str__(self):
        return f"Digest({self.user}, {self.date})"


class DigestEntry(models.Model):
    digest = models.ForeignKey(Digest, on_delete=models.CASCADE, related_name="entries")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    rank = models.IntegerField()
    score = models.FloatField(default=0.0)
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = [("digest", "item")]
        indexes = [models.Index(fields=["digest", "rank"])]


class UserItemState(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    is_read = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    is_later = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "item")]
        indexes = [models.Index(fields=["user", "updated_at"])]
