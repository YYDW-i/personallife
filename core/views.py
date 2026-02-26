from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from profiles.models import HealthProfile
from profiles.zhipu_client import get_health_analysis
import hashlib
from django.utils import timezone

def make_signature(profile: HealthProfile) -> str:
    raw = f"{profile.height_cm}|{profile.weight_kg}|{profile.age_year}|{profile.gender}|{profile.exercise_frequency}|{profile.exercise_time_minutes}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

@login_required
def dashboard(request):
    profile = HealthProfile.objects.filter(user=request.user).first()
    has_basic = (profile is not None and profile.height_cm is not None and profile.weight_kg is not None and profile.age_year is not None and profile.exercise_frequency is not None and profile.exercise_time_minutes is not None)
    
    ai_summary = ""
    ai_status = ""
    if has_basic:
    # 组织 prompt，写成一句清晰要求模型分析
        sig = make_signature(profile)

        # ✅ 命中缓存：数据没变 + 有旧结果
        if profile.ai_signature == sig and profile.ai_summary:
            ai_summary = profile.ai_summary
            ai_status = profile.ai_status or ""
        else:
            height = profile.height_cm
            weight = profile.weight_kg
            age = profile.age_year
            gender=profile.gender
            exercise_frequency = profile.exercise_frequency
            exercise_time_minutes = profile.exercise_time_minutes
            prompt = (
                f"用户身高：{height} cm，体重：{weight} kg，年龄：{age} 岁，性别（男：M女：F）：{gender}，运动频率（次/周）：{exercise_frequency}，运动时间（分钟/次）：{exercise_time_minutes}。"
                "请根据这些数据生成一份针对用户个性化详细的健康分析报告，"
                "综合用户的这些信息，包括 BMI 指标解释、是否存在超重或偏瘦风险、"
                "建议的生活习惯改善措施等。"
                "注意：输出的时候不要用markdown格式，不要使用星号或者其他语法特殊符号，否则输出到html里会出现很多乱码"
                "最后一行给出一个总结性的健康状态评价，（不要有类似“总结性健康状态评价：”的标题，因为我已经写好标题了）记住，评价内容都要在最后一行"
            )

            try:
                result = get_health_analysis(prompt)
                # result 里应该包含整个文本，比如：
                # “BMI 是 XX，属于正常范围。健康建议 …”
                # 你可以再做一些拆分，但最简单是渲染到模板
                # 也可以再做一次简单的提取
                lines = result.split("\n")
                # 最后一行作为状态总结（如果模型输出结构清晰）
                if len(lines) > 1:
                    ai_status = lines[-1]
                    ai_summary = "\n".join(lines[:-1])
                else:
                    ai_summary = result
                    ai_status = ""
                profile.ai_summary = ai_summary
                profile.ai_status = ai_status
                profile.ai_signature = sig
                profile.ai_updated_at = timezone.now()
                profile.save(update_fields=["ai_summary","ai_status","ai_signature","ai_updated_at"])
                profile.refresh_from_db()
                
            except Exception as e:
                ai_summary = f"AI 生成失败，请稍后再试: {str(e)}"

    return render(request,"core/dashboard.html",
                {"has_basic": has_basic,
                "ai_summary": ai_summary,
                "ai_status": ai_status,
                "profile": profile}
    )