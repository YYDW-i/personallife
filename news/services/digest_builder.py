from django.db import transaction
from django.utils import timezone
from .ranker import score_item
from news.models import Digest, DigestEntry, UserItemState, Item

def build_digest_for_user(user, date, pref, candidates, ranking_params):
    # candidates: queryset/list[Item]
    # 过滤屏蔽
    blocked_item_ids = set(UserItemState.objects.filter(user=user, is_blocked=True).values_list("item_id", flat=True))
    filtered = [it for it in candidates if it.id not in blocked_item_ids]

    # 打分排序
    scored = []
    for it in filtered:
        s = score_item(it, pref, source_weight=it.source.weight if it.source_id else 1.0, params=ranking_params)
        scored.append((s, it))
    scored.sort(key=lambda x: x[0], reverse=True)

    topn = scored[:pref.daily_limit]

    with transaction.atomic():
        digest, _ = Digest.objects.get_or_create(user=user, date=date)
        digest.entries.all().delete()
        for idx, (s, it) in enumerate(topn, start=1):
            DigestEntry.objects.create(digest=digest, item=it, rank=idx, score=float(s), reason="")
    return digest
