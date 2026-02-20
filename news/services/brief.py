from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from news.models import UserNewsPreference, NewsItem, DailyBrief, BriefEntry
from news.services.summarizer import summarize_item


def _match_keywords(item: NewsItem, keywords: list[str]) -> bool:
    if not keywords:
        return True
    hay = f"{item.title}\n{item.rss_summary}\n{item.content_text}".lower()
    return any(k.lower() in hay for k in keywords)


@transaction.atomic
def build_brief_for_user(user, date=None) -> DailyBrief:
    date = date or timezone.localdate()

    pref, _ = UserNewsPreference.objects.get_or_create(
        user=user,
        defaults={"max_items": getattr(settings, "NEWS_DEFAULT_MAX_ITEMS", 8)},
    )
    if not pref.enabled:
        # 没启用就不生成
        return None

    # 取最近 36 小时的新闻（跨时区、凌晨也不空）
    since = timezone.now() - timedelta(hours=36)

    topics = list(pref.topics.all())
    sources_qs = None
    if topics:
        sources_qs = NewsItem.objects.filter(
            source__is_active=True,
            source__topics__in=topics,
            fetched_at__gte=since,
        ).distinct()
    else:
        sources_qs = NewsItem.objects.filter(source__is_active=True, fetched_at__gte=since)

    # 语言/地区（可选过滤）
    if pref.language:
        sources_qs = sources_qs.filter(source__language=pref.language)
    if pref.region:
        sources_qs = sources_qs.filter(source__region=pref.region)

    items = sources_qs.select_related("source").order_by("-published_at", "-fetched_at")[:200]

    picked = []
    keywords = pref.keyword_list()
    for it in items:
        if _match_keywords(it, keywords):
            picked.append(it)
        if len(picked) >= pref.max_items:
            break

    brief, _ = DailyBrief.objects.get_or_create(user=user, date=date, language=pref.language or "zh")
    brief.entries.all().delete()

    for idx, it in enumerate(picked):
        summary = summarize_item(it, brief.language)
        BriefEntry.objects.create(
            brief=brief,
            item=it,
            title=it.title,
            summary=summary,
            url=it.link,
            source_name=it.source.name,
            score=1000 - idx,  # 简单排名：越新越靠前
        )

    return brief


def build_briefs_for_all_users(date=None) -> int:
    from django.contrib.auth import get_user_model
    User = get_user_model()

    count = 0
    for u in User.objects.all():
        b = build_brief_for_user(u, date=date)
        if b:
            count += 1
    return count