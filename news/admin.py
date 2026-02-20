from django.contrib import admin
from .models import Topic, NewsSource, NewsItem, UserNewsPreference, DailyBrief, BriefEntry


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "order")
    search_fields = ("slug", "name")


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "language", "region", "is_active", "weight", "rss_url")
    list_filter = ("language", "region", "is_active")
    search_fields = ("name", "rss_url")
    filter_horizontal = ("topics",)


@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "published_at", "fetched_at")
    list_filter = ("source",)
    search_fields = ("title", "link")


@admin.register(UserNewsPreference)
class UserNewsPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "enabled", "language", "region", "max_items", "keywords")
    filter_horizontal = ("topics",)


class BriefEntryInline(admin.TabularInline):
    model = BriefEntry
    extra = 0


@admin.register(DailyBrief)
class DailyBriefAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "language", "created_at")
    inlines = [BriefEntryInline]