from django import forms
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from .models import Task
import datetime


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
            "due_at": forms.TextInput(attrs={
                "class": "datepicker",
                "placeholder": "年-月-日 时:分"
            }),
            "window_start": forms.TextInput(attrs={
                "class": "datepicker",
                "placeholder": "年-月-日 时:分"
            }),
            "window_end": forms.TextInput(attrs={
                "class": "datepicker",
                "placeholder": "年-月-日 时:分"
            }),
        }

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("schedule_kind")
        remind_enabled = cleaned.get("remind_enabled")
        lead = cleaned.get("remind_lead_minutes") or 0

        def ensure_aware(value):
            """将输入转换为 aware datetime 对象，支持字符串或已有 datetime"""
            if value is None or value == '':
                return None

            # 如果已经是 datetime 对象，确保时区
            if isinstance(value, datetime.datetime):
                if timezone.is_naive(value):
                    return timezone.make_aware(value, timezone.get_current_timezone())
                return value

            # 如果是字符串，预处理后解析
            if isinstance(value, str):
                # 将 "YYYY-MM-DD HH:MM" 转换为 "YYYY-MM-DDTHH:MM:SS"
                if ' ' in value:
                    value = value.replace(' ', 'T')
                if value.count(':') == 1:  # 只有 HH:MM，补上秒数
                    value += ':00'
                dt = parse_datetime(value)
                if dt and timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                return dt

            # 其他情况尝试转为字符串后解析（通常不会发生）
            try:
                dt = parse_datetime(str(value))
                if dt and timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                return dt
            except:
                return None

        due_at = ensure_aware(cleaned.get("due_at"))
        ws = ensure_aware(cleaned.get("window_start"))
        we = ensure_aware(cleaned.get("window_end"))

        # 将转换后的 datetime 对象存回 cleaned_data
        cleaned['due_at'] = due_at
        cleaned['window_start'] = ws
        cleaned['window_end'] = we

        # 后续原有的校验逻辑保持不变（使用 due_at, ws, we 变量）
        if kind == Task.ScheduleKind.NONE:
            cleaned['due_at'] = cleaned['window_start'] = cleaned['window_end'] = None

        elif kind == Task.ScheduleKind.AT:
            if not due_at:
                self.add_error("due_at", "选择“绝对时刻”时必须填写到期时间。")
            cleaned['window_start'] = cleaned['window_end'] = None

        elif kind == Task.ScheduleKind.WINDOW:
            if not ws:
                self.add_error("window_start", "选择“时间段”时必须填写开始时间。")
            if not we:
                self.add_error("window_end", "选择“时间段”时必须填写结束时间。")
            elif ws and we and we <= ws:
                self.add_error("window_end", "结束时间必须晚于开始时间。")
            cleaned['due_at'] = None

        # 提醒校验
        base_time = due_at if kind == Task.ScheduleKind.AT else ws
        if remind_enabled:
            if not base_time:
                self.add_error("remind_enabled", "开启提醒前，请先设置任务时间。")
            else:
                cleaned['remind_at'] = base_time - datetime.timedelta(minutes=lead)
        else:
            cleaned['remind_at'] = None

        return cleaned
