from django.urls import path
from . import views

app_name = "news"

urlpatterns = [
    path("", views.news_home, name="home"),
    path("history/", views.news_history, name="history"),
    path("digest/<str:date>/", views.digest_detail, name="digest_detail"),
    path("item/<int:item_id>/", views.item_detail, name="item_detail"),
    path("preferences/", views.preferences, name="preferences"),

    path("item/<int:item_id>/toggle/", views.toggle_item_state, name="toggle_item_state"),
]
