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
            changed = set(form.changed_data)  # changed_data/has_changed 是 Django Forms API 的标准能力 :contentReference[oaicite:1]{index=1}
            obj = form.save()

            if {"height_cm", "weight_kg", "age_year"} & changed:
                obj.ai_summary = ""
                obj.ai_status = ""
                obj.ai_signature = ""
                obj.ai_updated_at = None
                obj.save(update_fields=["ai_summary", "ai_status", "ai_signature", "ai_updated_at"])

            return redirect("core:dashboard")
    else:
        form = HealthProfileForm(instance=profile)

    return render(request, "profiles/settings.html", {"form": form})
