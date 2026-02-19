from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False, help_text="可选，用于找回密码/通知")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        # 如果你想强制邮箱唯一（可选）：
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("这个邮箱已被注册。")
        return email
