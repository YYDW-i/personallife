from django.urls import path

from . import views

app_name = "deeplearning"

urlpatterns = [
    path("", views.builder, name="builder"),
    path("generate-code/", views.generate_code_api, name="generate_code"),
    path("start-training/", views.start_training_api, name="start_training"),
    path("training-status/<str:job_id>/", views.training_status_api, name="training_status"),
]