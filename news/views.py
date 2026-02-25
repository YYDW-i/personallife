from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from news.forms import NewsPreferenceForm
from news.models import UserNewsPreference, DailyBrief
from news.services.brief import build_brief_for_user
from news.services.fetcher import fetch_all_sources
from django.contrib import messages
from django.http import JsonResponse

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