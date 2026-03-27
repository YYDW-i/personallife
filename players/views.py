from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy

from .models import UserProfile
from .forms import UserBasicForm, UserProfileForm

@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user_form = UserBasicForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "个人资料已更新。")
            return redirect("players:profile")
    else:
        user_form = UserBasicForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile)

    return render(
        request,
        "players/profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "profile": profile,
        },
    )

class MyPasswordChangeView(PasswordChangeView):
    template_name = "players/password_change.html"
    success_url = reverse_lazy("players:password_change_done")

class MyPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "players/password_change_done.html"