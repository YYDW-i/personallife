
# Create your views here.
from django.contrib import messages
from django.contrib.auth import login,logout
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from .forms import RegisterForm

def register(request):
    if request.user.is_authenticated:
        logout(request)  # 清掉原账号登录态（这样你就能注册新账号了）

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)     # 登录新注册的账号
        return redirect("core:dashboard")

    return render(request, "accounts/register.html", {"form": form})
