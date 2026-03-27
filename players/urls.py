from django.urls import path
from . import views

app_name = "players"

urlpatterns = [
    path("profile/", views.profile_view, name="profile"),
    path("password/", views.MyPasswordChangeView.as_view(), name="password_change"),
    path("password/done/", views.MyPasswordChangeDoneView.as_view(), name="password_change_done"),
]