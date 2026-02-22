from django import forms
from news.models import UserNewsPreference, Topic


class NewsPreferenceForm(forms.ModelForm):
    topics = forms.ModelMultipleChoiceField(
        queryset=Topic.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="新闻主题",
    )

    class Meta:
        model = UserNewsPreference
        fields = ["enabled", "language", "region", "keywords", "max_items", "topics"]
        widgets = {
            "keywords": forms.TextInput(attrs={"placeholder": "逗号分隔：AI, 芯片, 体育…"}),
            "language": forms.TextInput(attrs={"placeholder": "中文：zh 英文：en"}),
            "region": forms.TextInput(attrs={"placeholder": "中国:CN 外国：INTER"}),
        }
        labels = {
            "enabled": "启用新闻管家",
            "language": "语言",
            "region": "地区",
            "keywords": "关键词",
            "max_items": "每日条数",
        }