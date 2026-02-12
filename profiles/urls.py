from django.urls import path
from . import views

app_name = "profiles"

urlpatterns = [
    path("", views.settings_view, name="settings"),
    path("submit/", views.submit_form, name="submit"),
]
