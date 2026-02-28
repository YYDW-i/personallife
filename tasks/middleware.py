# tasks/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from .models import Task

class FocusModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 只对已认证用户生效
        if request.user.is_authenticated:
            now = timezone.now()
            # 查找当前处于“时间段”内且未完成的任务（取第一个）
            active_task = Task.objects.filter(
                user=request.user,
                status=Task.Status.TODO,
                schedule_kind=Task.ScheduleKind.WINDOW,
                window_start__lte=now,
                window_end__gte=now
            ).first()

            if active_task:
                # 豁免路径：专注页本身、静态文件、API、管理员后台
                exempt_paths = [
                    reverse('tasks:focus', args=[active_task.id]),  # 当前任务的专注页
                    '/static/',
                    '/tasks/api/',
                    '/admin/',
                ]
                if not any(request.path.startswith(p) for p in exempt_paths):
                    return redirect('tasks:focus', task_id=active_task.id)

        return self.get_response(request)