from django.urls import path
from . import views, views_api

app_name = "maths"

urlpatterns = [
    path("", views.maths_home, name="home"),
    path("api/eval/", views_api.api_eval, name="api_eval"),
    path("api/plot/", views_api.api_plot, name="api_plot"),
]