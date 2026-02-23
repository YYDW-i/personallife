from django.urls import path
from . import views

app_name = "analytics_app"

urlpatterns = [
    path("", views.index, name="index"),

    # I Ching
    path("iching/", views.iching_index, name="iching_index"),
    path("iching/cast/", views.iching_cast, name="iching_cast"),
]