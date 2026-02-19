from __future__ import annotations

import re
from typing import List

from django import forms
from django.core.exceptions import ValidationError

from .models import UserPreference, Category


def _normalize_keywords(raw: str) -> str:
    """
    把用户输入的关键词（逗号/分号/换行/空格分隔）规范化成“每行一个关键词”的存储格式：
    - 去空
    - 去重
    - 保序（尽量）
    """
    if not raw:
        return ""

    # 逗号/中文逗号/分号/中文分号/换行/制表符/多个空格 都当分隔符
    parts = re.split(r"[,\uFF0C;\uFF1B\n\r\t]+", raw)
    cleaned: List[str] = []
    seen = set()
    for p in parts:
        w = (p or "").strip()
        if not w:
            continue
        lw = w.lower()
        if lw in seen:
            continue
        seen.add(lw)
        cleaned.append(w)

    return "\n".join(cleaned)


class PreferenceForm(forms.ModelForm):
    # 你希望 daily_limit 只给几个档位，就用 ChoiceField 更直观
    DAILY_CHOICES = (
        (10, "10 条/天"),
        (20, "20 条/天"),
        (30, "30 条/天"),
    )
    daily_limit = forms.ChoiceField(
        choices=DAILY_CHOICES,
        label="每日条数上限",
        initial=20,
        help_text="建议 10–30 条，先保证信息密度。",
    )

    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="订阅频道/主题（可多选）",
    )

    push_time = forms.TimeField(
        required=True,
        label="推送时间",
        widget=forms.TimeInput(attrs={"type": "time"}),
        help_text="例如 08:00 或 18:00",
    )

    include_keywords = forms.CharField(
        required=False,
        label="关键词（可选）",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "例如：AI, 大模型, 运动科学（逗号/换行分隔）"}),
    )
    exclude_keywords = forms.CharField(
        required=False,
        label="排除词（可选）",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "例如：八卦, 广告, 带货（逗号/换行分隔）"}),
    )

    class Meta:
        model = UserPreference
        fields = [
            "categories",
            "language",
            "region",
            "include_keywords",
            "exclude_keywords",
            "daily_limit",
            "push_time",
            "include_academic",
        ]
        widgets = {
            "language": forms.TextInput(attrs={"placeholder": "例如：zh / en（留空=不限）"}),
            "region": forms.TextInput(attrs={"placeholder": "例如：CN / US / Global（留空=不限）"}),
        }

    def clean_daily_limit(self):
        # ChoiceField 会给出字符串，要转 int
        val = int(self.cleaned_data["daily_limit"])
        if val not in (10, 20, 30):
            raise ValidationError("daily_limit 必须是 10/20/30 之一。")
        return val

    def clean(self):
        cleaned = super().clean()

        # 关键词规范化（存储为每行一个，便于后端 splitlines）
        cleaned["include_keywords"] = _normalize_keywords(cleaned.get("include_keywords", ""))
        cleaned["exclude_keywords"] = _normalize_keywords(cleaned.get("exclude_keywords", ""))

        # 一个简单的现实约束：别让用户填太离谱
        inc = cleaned.get("include_keywords", "")
        exc = cleaned.get("exclude_keywords", "")
        if len(inc.splitlines()) > 50:
            self.add_error("include_keywords", "关键词太多了（>50），先精简一些。")
        if len(exc.splitlines()) > 50:
            self.add_error("exclude_keywords", "排除词太多了（>50），先精简一些。")

        return cleaned
