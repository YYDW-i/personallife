from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from news.forms import NewsPreferenceForm
from news.models import UserNewsPreference, DailyBrief
from news.services.brief import build_brief_for_user


@login_required
def index(request):
    date = timezone.localdate()
    brief = DailyBrief.objects.filter(user=request.user, date=date).prefetch_related("entries").first()
    print(f"brief: {brief}")
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
    # 手动刷新：立即为当前用户生成一次今日简报
        build_brief_for_user(request.user, date=timezone.localdate())
    return redirect("news:index")