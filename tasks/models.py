from django.conf import settings
from django.db import models
from django.utils import timezone


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "TODO", "待完成"
        DONE = "DONE", "已完成"

    class ScheduleKind(models.TextChoices):
        NONE = "NONE", "不设置时间"
        AT = "AT", "绝对时刻"
        WINDOW = "WINDOW", "时间段"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")

    title = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")

    status = models.CharField(max_length=8, choices=Status.choices, default=Status.TODO)

    # 时间：绝对时刻 or 时间段
    schedule_kind = models.CharField(max_length=10, choices=ScheduleKind.choices, default=ScheduleKind.NONE)
    due_at = models.DateTimeField(null=True, blank=True)          # AT 用
    window_start = models.DateTimeField(null=True, blank=True)    # WINDOW 用
    window_end = models.DateTimeField(null=True, blank=True)      # WINDOW 用

    # 提醒：到点提醒（remind_at 是实际触发时间，remind_lead_minutes 是提前量）
    remind_enabled = models.BooleanField(default=False)
    remind_lead_minutes = models.PositiveIntegerField(default=0)  # 提前多少分钟提醒
    remind_at = models.DateTimeField(null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True)     # 防止重复提醒

    # 完成信息
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def mark_done(self):
        self.status = self.Status.DONE
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])

    def __str__(self):
        return f"Task({self.user_id}, {self.title}, {self.status})"
