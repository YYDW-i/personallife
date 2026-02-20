from django.urls import path
from . import views

app_name = "news"

urlpatterns = [
    path("", views.index, name="index"),
    path("preferences/", views.preferences, name="preferences"),
    path("refresh/", views.refresh_today, name="refresh_today"),
]