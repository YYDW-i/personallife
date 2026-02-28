from django.urls import path
from .views import (
    TaskListView, TaskCreateView, TaskUpdateView, TaskDeleteView,
    complete_task, reminders_api, focus_view, active_focus_api
)

app_name = "tasks"

urlpatterns = [
    path("", TaskListView.as_view(), name="index"),
    path("new/", TaskCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", TaskUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", TaskDeleteView.as_view(), name="delete"),

    path('focus/<int:task_id>/', focus_view, name='focus'),

    # 完成任务：和 delete 分开，按钮也分开
    path("<int:pk>/complete/", complete_task, name="complete"),

    path('api/active-focus/', active_focus_api, name='active_focus_api'),

    # 提醒轮询接口
    path("api/reminders/", reminders_api, name="reminders_api"),
]
