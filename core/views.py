from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from profiles.models import HealthProfile
from profiles.zhipu_client import get_health_analysis
@login_required
def dashboard(request):
    profile = HealthProfile.objects.filter(user=request.user).first()
    has_basic = (profile is not None and profile.height_cm is not None and profile.weight_kg is not None and profile.age_year is not None)
    
    ai_summary = ""
    ai_status = ""
    if has_basic:
    # 组织 prompt，写成一句清晰要求模型分析
        height = profile.height_cm
        weight = profile.weight_kg
        age = profile.age_year
        prompt = (
            f"用户身高：{height} cm，体重：{weight} kg，年龄：{age} 岁。"
            "请根据这些数据生成一份详细的健康分析报告，"
            "包括 BMI 指标解释、是否存在超重或偏瘦风险、"
            "建议的生活习惯改善措施等。"
            "最后给出一个总结性的健康状态结论"
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
        except Exception as e:
            ai_summary = f"AI 生成失败，请稍后再试: {str(e)}"
    print(">>> core.dashboard called")
    print(">>> profile:", profile)
    if profile:
        print(">>> height_cm:", profile.height_cm, "weight_kg:", profile.weight_kg, "age_year:", profile.age_year)
    print(">>> has_basic:", has_basic)


    return render(request,"core/dashboard.html",
                {"has_basic": has_basic,
                "ai_summary": ai_summary,
                "ai_status": ai_status,
                "profile": profile}
    )