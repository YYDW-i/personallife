from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.utils import timezone

from .models import Task
from .forms import TaskForm


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/task_list.html"
    context_object_name = "tasks"

    def get_queryset(self):
        # 只看自己的任务
        qs = Task.objects.filter(user=self.request.user)
        # 未完成优先，再按提醒/时间排序
        return qs.order_by("status", "remind_at", "due_at", "window_start", "-created_at")


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"
    success_url = reverse_lazy("tasks:index")

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        # 如果重新设置了提醒时间，允许再次提醒
        obj.reminded_at = None
        obj.save()
        return redirect(self.success_url)


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"
    success_url = reverse_lazy("tasks:index")

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def form_valid(self, form):
        obj = form.save(commit=False)
        # 更新后如果提醒时间变化，也允许再次提醒
        obj.reminded_at = None
        obj.save()
        return redirect(self.success_url)


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    template_name = "tasks/task_confirm_delete.html"
    success_url = reverse_lazy("tasks:index")

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)


@require_POST
def complete_task(request, pk: int):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if task.status != Task.Status.DONE:
        task.mark_done()
    return redirect("tasks:index")


def reminders_api(request):
    """
    返回“到点需要提醒”的任务（只返回一次：用 reminded_at 去重）
    前端轮询这个接口即可做提醒。
    """
    if not request.user.is_authenticated:
        return JsonResponse({"reminders": []})

    now = timezone.now()  # USE_TZ=True 时是时区感知 datetime :contentReference[oaicite:4]{index=4}

    qs = Task.objects.filter(
        user=request.user,
        status=Task.Status.TODO,
        remind_enabled=True,
        remind_at__isnull=False,
        remind_at__lte=now,
        reminded_at__isnull=True,
    ).order_by("remind_at")[:20]

    reminders = []
    for t in qs:
        when = t.remind_at
        reminders.append({
            "id": t.id,
            "title": t.title,
            "kind": t.schedule_kind,
            "remind_at": timezone.localtime(when).isoformat() if when else None,
        })

    # 标记已提醒，避免重复弹
    Task.objects.filter(id__in=[r["id"] for r in reminders]).update(reminded_at=now)

    return JsonResponse({"now": timezone.localtime(now).isoformat(), "reminders": reminders})
