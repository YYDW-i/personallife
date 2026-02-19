from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import JsonResponse
from .models import Digest, Item, UserPreference, UserItemState
from .forms import PreferenceForm
from collections import defaultdict
from django.db.models import Prefetch


def _build_rows_for_digest(user, digest):
    """
    返回 rows: [{title: '科技', items: [{item, state}, ...]}, ...]
    按 source.categories 分组；没有类别的进 “其他”。
    """
    if not digest:
        return []

    entries = digest.entries.select_related("item", "item__source").prefetch_related("item__source__categories").order_by("rank")

    # 预取用户状态（避免 N+1）
    item_ids = [e.item_id for e in entries]
    states = UserItemState.objects.filter(user=user, item_id__in=item_ids)
    state_map = {s.item_id: s for s in states}

    grouped = defaultdict(list)
    for e in entries:
        item = e.item
        cats = list(item.source.categories.all()) if item.source_id else []
        if cats:
            key = cats[0].name  # MVP：先按第一个 category 分组（后续可多标签）
        else:
            key = "其他"
        grouped[key].append({
            "item": item,
            "state": state_map.get(item.id),
        })

    # 保序：按组内第一条 rank 的先后
    ordered_keys = sorted(grouped.keys(), key=lambda k: min([idx for idx, x in enumerate(grouped[k])], default=999999))
    rows = [{"title": k, "items": grouped[k]} for k in ordered_keys]
    return rows

@login_required
def news_home(request):
    today = timezone.localdate()
    digest = Digest.objects.filter(user=request.user, date=today).prefetch_related("entries__item__source").first()
    rows = _build_rows_for_digest(request.user, digest)
    return render(request, "news/home.html", {"digest": digest, "today": today, "rows": rows})

@login_required
def news_history(request):
    digests = Digest.objects.filter(user=request.user).order_by("-date")[:60]
    return render(request, "news/history.html", {"digests": digests})

@login_required
def digest_detail(request, date):
    digest = get_object_or_404(Digest, user=request.user, date=date)
    rows = _build_rows_for_digest(request.user, digest)
    return render(request, "news/digest_detail.html", {"digest": digest, "rows": rows})

@login_required
def item_detail(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    state, _ = UserItemState.objects.get_or_create(user=request.user, item=item)
    if not state.is_read:
        state.is_read = True
        state.save(update_fields=["is_read", "updated_at"])
    return render(request, "news/item_detail.html", {"item": item, "state": state})

@login_required
def preferences(request):
    pref, _ = UserPreference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = PreferenceForm(request.POST, instance=pref)
        if form.is_valid():
            form.save()
            return redirect("news:home")
    else:
        form = PreferenceForm(instance=pref)
    return render(request, "news/preferences.html", {"form": form})

@login_required
def toggle_item_state(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    state, _ = UserItemState.objects.get_or_create(user=request.user, item=item)

    field = request.POST.get("field")  # is_read/is_favorite/is_later/is_blocked
    if field in {"is_read","is_favorite","is_later","is_blocked"}:
        new_val = not getattr(state, field)
        setattr(state, field, new_val)
        state.save(update_fields=[field, "updated_at"])
    else:
        new_val = None

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if is_ajax:
        return JsonResponse({"ok": True, "field": field, "value": new_val})

    # 非 AJAX：回到来源页（Digest/Item/Home 都行）
    return redirect(request.META.get("HTTP_REFERER", "news:home"))