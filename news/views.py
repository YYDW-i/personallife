from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from news.forms import NewsPreferenceForm
from news.models import UserNewsPreference, DailyBrief
from news.services.brief import build_brief_for_user
from news.services.fetcher import fetch_all_sources
from django.contrib import messages
from django.http import JsonResponse

from news.models import NewsItem

@login_required
def index(request):
    date = timezone.localdate()

    pref, _ = UserNewsPreference.objects.get_or_create(user=request.user)
    lang = pref.language or 'zh'

    brief = DailyBrief.objects.filter(user=request.user, date=date,language=lang).prefetch_related("entries").first()
    return render(request, "news/index.html", {"brief": brief, "date": date})


@login_required
def preferences(request):
    pref, _ = UserNewsPreference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = NewsPreferenceForm(request.POST, instance=pref)
        if form.is_valid():
            form.save()
            return redirect("news:index")
    else:
        form = NewsPreferenceForm(instance=pref)
    return render(request, "news/preferences.html", {"form": form})


@login_required
def refresh_today(request):
    if request.method == "POST":
        new_count = fetch_all_sources()
        build_brief_for_user(request.user, date=timezone.localdate())
        # 判断是否为 AJAX 请求（通过请求头 X-Requested-With）
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": True, "new_count": new_count})
        return redirect("news:index")
    return redirect("news:index")

@login_required
def sync_news(request):
    """只执行抓取新闻源，不生成简报"""
    if request.method == "POST":
        # 执行抓取（耗时操作）
        new_count = fetch_all_sources()
        # 判断是否为 AJAX 请求
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": True, "new_count": new_count})
        # 普通 POST 则重定向到简报页，并显示成功消息
        messages.success(request, f"新闻同步完成，新增 {new_count} 条。")
        return redirect("news:index")
    # 非 POST 请求重定向到首页
    return redirect("news:index")


@login_required
def filter_news(request):
    """只基于已有新闻重新生成简报，不抓取"""
    if request.method == "POST":
        date = timezone.localdate()
        if not NewsItem.objects.exists():
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"success": False, "error": "暂无新闻，请先同步。"})
            messages.error(request, "暂无新闻，请先点击“同步更新新闻”。")
            return redirect("news:index")
        # 生成简报
        brief = build_brief_for_user(request.user, date=date)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": True, "brief_created": bool(brief)})
        messages.success(request, "简报已重新生成。")
        return redirect("news:index")
    return redirect("news:index")