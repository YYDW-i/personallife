from datetime import timedelta
from django import forms
from django.utils import timezone
from .models import Task


class TaskForm(forms.ModelForm):
    # 额外字段：相对时间段（持续分钟数）

    class Meta:
        model = Task
        fields = [
            "title", "description",
            "schedule_kind", "due_at", "window_start", "window_end",
            "remind_enabled", "remind_lead_minutes",
        ]
        widgets = {
            "due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "window_start": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "window_end": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def clean(self):
        cleaned = super().clean()

        kind = cleaned.get("schedule_kind")
        due_at = cleaned.get("due_at")
        ws = cleaned.get("window_start")
        we = cleaned.get("window_end")

        remind_enabled = cleaned.get("remind_enabled")
        lead = cleaned.get("remind_lead_minutes") or 0

        # 1) 时间校验 + 统一清理无关字段
        if kind == Task.ScheduleKind.NONE:
            cleaned["due_at"] = None
            cleaned["window_start"] = None
            cleaned["window_end"] = None

        elif kind == Task.ScheduleKind.AT:
            if not due_at:
                self.add_error("due_at", "选择“绝对时刻”时必须填写到期时间。")
            cleaned["window_start"] = None
            cleaned["window_end"] = None

        elif kind == Task.ScheduleKind.WINDOW:
            if not ws:
                self.add_error("window_start", "选择“时间段”时必须填写开始时间。")
            if ws and not we:
                self.add_error("window_end", "时间段需要填写结束时间，或填写“持续时长（分钟）”。")
            if ws and we and we <= ws:
                self.add_error("window_end", "结束时间必须晚于开始时间。")
            cleaned["due_at"] = None

        # 2) 提醒校验：开启提醒必须有一个“基准时间”
        base_time = None
        kind2 = cleaned.get("schedule_kind")
        if kind2 == Task.ScheduleKind.AT:
            base_time = cleaned.get("due_at")
        elif kind2 == Task.ScheduleKind.WINDOW:
            base_time = cleaned.get("window_start")

        if remind_enabled:
            if not base_time:
                self.add_error("remind_enabled", "开启提醒前，请先设置任务时间（绝对时刻或时间段）。")
            else:
                cleaned["remind_at"] = base_time - timedelta(minutes=lead)
        else:
            cleaned["remind_at"] = None
            # 不强制清 reminded_at：但更合理是把它清掉，让你下次开启提醒能触发
            # 这里不动，由 save() 逻辑决定

        return cleaned
