from django import forms
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()

class UserBasicForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]
        labels = {
            "username": "账号",
            "email": "邮箱",
        }
        widgets = {
            "username": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["nickname", "signature", "bio", "phone", "location", "website", "birthday", "avatar"]
        labels = {
            "nickname": "昵称",
            "signature": "个性签名",
            "bio": "个人简介",
            "phone": "手机号",
            "location": "所在地",
            "website": "个人网站",
            "birthday": "生日",
            "avatar": "头像",
        }
        widgets = {
            "nickname": forms.TextInput(attrs={"class": "input"}),
            "signature": forms.TextInput(attrs={"class": "input"}),
            "bio": forms.Textarea(attrs={"class": "input", "rows": 4}),
            "phone": forms.TextInput(attrs={"class": "input"}),
            "location": forms.TextInput(attrs={"class": "input"}),
            "website": forms.URLInput(attrs={"class": "input"}),
            "birthday": forms.DateInput(attrs={"class": "input", "type": "date"}),
        }