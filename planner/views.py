import calendar
from collections import defaultdict
from datetime import datetime, date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from tasks.models import Task

from .holidays import get_day_events


def _month_range(year: int, month: int):
    """返回 [month_start, month_end) 的 tz-aware datetime"""
    tz = timezone.get_current_timezone()
    start_naive = datetime(year, month, 1, 0, 0, 0)
    month_start = timezone.make_aware(start_naive, tz)

    if month == 12:
        end_naive = datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        end_naive = datetime(year, month + 1, 1, 0, 0, 0)
    month_end = timezone.make_aware(end_naive, tz)
    return month_start, month_end


def _prev_next_month(year: int, month: int):
    if month == 1:
        return (year - 1, 12), (year, 2)
    if month == 12:
        return (year, 11), (year + 1, 1)
    return (year, month - 1), (year, month + 1)


@login_required
def calendar_month(request, year=None, month=None):
    now = timezone.localtime()
    year = int(year) if year else now.year
    month = int(month) if month else now.month

    month_start, month_end = _month_range(year, month)
    show_done = request.GET.get("show_done") == "1"

    base_qs = Task.objects.filter(user=request.user)
    if not show_done:
        base_qs = base_qs.filter(status=Task.Status.TODO)

    # 取出本月相关任务：
    qs = base_qs.filter(
        Q(schedule_kind=Task.ScheduleKind.AT, due_at__gte=month_start, due_at__lt=month_end)
        | Q(
            schedule_kind=Task.ScheduleKind.WINDOW,
            window_start__lt=month_end,
            window_end__gte=month_start,
        )
    ).select_related("user")

    # 按“日期”分组（key 用 'YYYY-MM-DD' 字符串）
    by_day = defaultdict(list)
    for t in qs:
        if t.schedule_kind == Task.ScheduleKind.AT and t.due_at:
            d = timezone.localtime(t.due_at).date()
            time_key = timezone.localtime(t.due_at).time()
        elif t.schedule_kind == Task.ScheduleKind.WINDOW and t.window_start:
            d = timezone.localtime(t.window_start).date()
            time_key = timezone.localtime(t.window_start).time()
        else:
            continue
        k = d.isoformat()
        by_day[k].append((time_key, t))

    # 每天内部按时间排序
    day_tasks = {}
    for k, lst in by_day.items():
        lst.sort(key=lambda x: x[0])  # 按时间排序
        day_tasks[k] = [t for _, t in lst]

    # 生成月历格子：周一为第一列（你习惯中文日历）
    cal = calendar.Calendar(firstweekday=0)  # 0=Monday
    weeks = []
    today = timezone.localtime().date()

    for week in cal.monthdatescalendar(year, month):
        row = []
        for d in week:
            events = get_day_events(d)
            row.append({
                "date": d,
                "date_str": d.isoformat(),
                "day": d.day,
                "in_month": (d.month == month),
                "is_today": (d == today),
                "tasks": day_tasks.get(d.isoformat(), []),  # 任务按日期分组
                "events": events,
            })
        weeks.append(row)

    (py, pm), (ny, nm) = _prev_next_month(year, month)

    floating = base_qs.filter(schedule_kind=Task.ScheduleKind.NONE).order_by("-created_at")[:10]

    return render(request, "planner/calendar_month.html", {
        "year": year,
        "month": month,
        "weeks": weeks,
        "prev_year": py, "prev_month": pm,
        "next_year": ny, "next_month": nm,
        "show_done": show_done,
        "floating_tasks": floating,
    })



@login_required
def calendar_day(request, year: int, month: int, day: int):
    target = date(year, month, day)
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime(year, month, day, 0, 0, 0), tz)
    end = start + timedelta(days=1)

    show_done = request.GET.get("show_done") == "1"
    base_qs = Task.objects.filter(user=request.user)
    if not show_done:
        base_qs = base_qs.filter(status=Task.Status.TODO)

    qs = base_qs.filter(
        Q(schedule_kind=Task.ScheduleKind.AT, due_at__gte=start, due_at__lt=end)
        | Q(schedule_kind=Task.ScheduleKind.WINDOW, window_start__lt=end, window_end__gte=start)
    ).order_by("due_at", "window_start", "-created_at")

    return render(request, "planner/calendar_day.html", {
        "target": target,
        "tasks": qs,
        "show_done": show_done,
    })
