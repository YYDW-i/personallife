from django.urls import path
from . import views

app_name = "news"

urlpatterns = [
    path("", views.index, name="index"),
    path("preferences/", views.preferences, name="preferences"),
    path("refresh_today/", views.refresh_today, name="refresh_today"),

    path("sync/", views.sync_news, name="sync_news"),          # 新增：同步抓取新闻
    path("filter/", views.filter_news, name="filter_news"),    # 新增：筛选生成简报
]