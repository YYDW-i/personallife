import hashlib
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from profiles.models import HealthProfile
from profiles.zhipu_client import get_health_analysis
from tasks.models import Task


def make_signature(profile):
    values = (profile.height_cm, profile.weight_kg, profile.age_year, profile.gender,
              profile.exercise_frequency, profile.exercise_time_minutes, profile.sleep_hours)
    return hashlib.sha256("|".join(map(str, values)).encode()).hexdigest()


@login_required
def dashboard(request):
    profile = HealthProfile.objects.filter(user=request.user).first()
    has_basic = profile is not None and all(value is not None for value in (
        profile.height_cm, profile.weight_kg, profile.age_year, profile.exercise_frequency,
        profile.exercise_time_minutes, profile.sleep_hours)) and bool(profile.gender)
    if request.method == "POST":
        if not has_basic:
            messages.error(request, "请先完善健康资料。")
        elif not settings.OPENAI_API_KEY:
            messages.info(request, "请在 .env 中配置 OPENAI_API_KEY 后使用 AI 分析。")
        else:
            prompt = (
                f"身高 {profile.height_cm} cm，体重 {profile.weight_kg} kg，年龄 {profile.age_year}，"
                f"性别 {profile.get_gender_display()}，每周运动 {profile.exercise_frequency} 次，"
                f"每次 {profile.exercise_time_minutes} 分钟，睡眠 {profile.sleep_hours} 小时。"
                "请给出中文生活习惯参考，不作疾病诊断。使用纯文本，最后一行概括建议。"
            )
            try:
                result = get_health_analysis(prompt)
                lines = [line.strip() for line in result.splitlines() if line.strip()]
                profile.ai_summary = "\n".join(lines[:-1]) if len(lines) > 1 else result
                profile.ai_status = lines[-1][:64] if len(lines) > 1 else "分析已更新"
                profile.ai_signature = make_signature(profile)
                profile.ai_updated_at = timezone.now()
                profile.save(update_fields=["ai_summary", "ai_status", "ai_signature", "ai_updated_at"])
                messages.success(request, "健康分析已更新。")
            except Exception:
                logging.getLogger(__name__).exception("健康分析失败")
                messages.error(request, "AI 分析暂时不可用，请检查密钥和网络后重试。")
        return redirect("core:dashboard")

    tasks = Task.objects.filter(user=request.user)
    total = tasks.count()
    done = tasks.filter(status=Task.Status.DONE).count()
    today = timezone.localdate()
    upcoming = tasks.filter(status=Task.Status.TODO).order_by("due_at", "window_start", "-created_at")[:4]
    bmi = None
    if profile and profile.height_cm and profile.height_cm > 0 and profile.weight_kg:
        bmi = round(float(profile.weight_kg) / (float(profile.height_cm) / 100) ** 2, 1)
    cached = bool(has_basic and profile.ai_signature == make_signature(profile))
    return render(request, "core/dashboard.html", {
        "profile": profile, "has_basic": has_basic, "bmi": bmi,
        "ai_summary": profile.ai_summary if cached else "",
        "ai_status": profile.ai_status if cached else "",
        "ai_enabled": bool(settings.OPENAI_API_KEY),
        "total_tasks": total, "done_tasks": done, "todo_tasks": total - done,
        "completion": round(done / total * 100) if total else 0,
        "upcoming_tasks": upcoming, "today": today,
    })
