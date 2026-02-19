from django.utils import timezone

def score_item(item, pref, source_weight=1.0, params=None):
    params = params or {}
    now = timezone.now()
    age_hours = max(0.0, (now - item.published_at).total_seconds() / 3600.0)
    freshness = max(0.0, 1.0 - age_hours / params.get("freshness_window_hours", 48))

    sw = source_weight * params.get("source_weight_scale", 1.0)

    match = 0.0
    # 类别/关键词命中：这里给骨架，具体用你的 categories & keyword tokenizer 实现
    match += params.get("base_match", 0.0)

    return (
        params.get("w_freshness", 1.0) * freshness +
        params.get("w_source", 0.6) * sw +
        params.get("w_match", 1.2) * match
    )
