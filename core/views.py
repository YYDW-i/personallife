from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from profiles.models import HealthProfile

@login_required
def dashboard(request):
    profile = HealthProfile.objects.filter(user=request.user).first()
    has_basic = (profile is not None and profile.height_cm is not None and profile.weight_kg is not None)
    return render(request, "core/dashboard.html",{
        "profile": profile,
        "has_basic": has_basic
    })
