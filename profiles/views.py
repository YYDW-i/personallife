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
