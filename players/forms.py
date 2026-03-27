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
            "username": forms.TextInput(attrs={
                "class": "profile-control",
                "placeholder": "输入账号名称",
                "autocomplete": "username",
            }),
            "email": forms.EmailInput(attrs={
                "class": "profile-control",
                "placeholder": "name@example.com",
                "autocomplete": "email",
            }),
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
            "nickname": forms.TextInput(attrs={
                "class": "profile-control",
                "placeholder": "你希望别人怎么称呼你",
            }),
            "signature": forms.TextInput(attrs={
                "class": "profile-control",
                "placeholder": "一句简短的个性签名",
                "maxlength": "120",
            }),
            "bio": forms.Textarea(attrs={
                "class": "profile-control profile-control-textarea",
                "rows": 5,
                "placeholder": "介绍一下你自己，写你希望别人认识你的哪一面",
            }),
            "phone": forms.TextInput(attrs={
                "class": "profile-control",
                "placeholder": "选填",
                "autocomplete": "tel",
            }),
            "location": forms.TextInput(attrs={
                "class": "profile-control",
                "placeholder": "例如：Wuhan / Frankfurt",
                "autocomplete": "address-level2",
            }),
            "website": forms.URLInput(attrs={
                "class": "profile-control",
                "placeholder": "https://your-site.com",
                "autocomplete": "url",
            }),
            "birthday": forms.DateInput(attrs={
                "class": "profile-control",
                "type": "date",
            }),
            "avatar": forms.ClearableFileInput(attrs={
                "class": "profile-file-input",
                "accept": "image/*",
            }),
        }