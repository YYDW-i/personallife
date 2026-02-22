from django.urls import path
from . import views

app_name = "math"

urlpatterns = [
    path("", views.index, name="index"),
]
