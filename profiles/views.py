# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import HealthProfile
from .forms import HealthProfileForm
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .zhipu_client import get_health_analysis

@login_required
def settings_view(request):
    profile, _ = HealthProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = HealthProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("core:dashboard")
    else:
        form = HealthProfileForm(instance=profile)

    return render(request, "profiles/settings.html", {"form": form})


def submit_form(request):
    if request.method == "POST":
        # 获取表单数据
        height = request.POST.get("height")
        weight = request.POST.get("weight")
        age = request.POST.get("age", "")

        # 组织 prompt，写成一句清晰要求模型分析
        prompt = (
            f"用户身高：{height} cm，体重：{weight} kg，年龄：{age} 岁。"
            "请根据这些数据生成一份详细的健康分析报告，"
            "包括 BMI 指标解释、是否存在超重或偏瘦风险、"
            "建议的生活习惯改善措施等。"
        )

        # 调用模型生成分析报告
        report = get_health_analysis(prompt)

        # 渲染到报告页面
        return render(request, "core/dashboard.html", {"report": report})

    # GET 请求就显示表单
    return render(request, "core/dashboard.html")
