from django.urls import path
from . import views

app_name = "planner"

urlpatterns = [
    path("", views.calendar_month, name="index"),
    path("<int:year>/<int:month>/", views.calendar_month, name="month"),
    path("day/<int:year>/<int:month>/<int:day>/", views.calendar_day, name="day"),
]
