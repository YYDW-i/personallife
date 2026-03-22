from django.urls import path
from . import views

app_name = "deeplearning"

urlpatterns = [
    path("", views.builder, name="builder"),
]
