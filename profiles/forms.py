from django import forms
from .models import HealthProfile

class HealthProfileForm(forms.ModelForm):
    height_cm = forms.DecimalField(label="身高（cm）", min_value=30, max_value=300, decimal_places=2)
    weight_kg = forms.DecimalField(label="体重（kg）", min_value=1, max_value=600, decimal_places=2)
    age_year = forms.IntegerField(label="年龄", min_value=1, max_value=120)
    gender = forms.ChoiceField(label="性别", choices=HealthProfile.GENDER_CHOICES)
    exercise_frequency = forms.IntegerField(label="运动频率（次 / 周）", min_value=0, max_value=100)
    exercise_time_minutes = forms.IntegerField(label="每次运动（分钟）", min_value=0, max_value=1440)
    sleep_hours = forms.DecimalField(label="每日睡眠（小时）", min_value=0, max_value=24, decimal_places=2)
    class Meta:
        model = HealthProfile
        fields = ["height_cm", "weight_kg","age_year","gender","exercise_frequency","exercise_time_minutes","sleep_hours"]
        widgets = {
            "height_cm": forms.NumberInput(attrs={"placeholder": "例如 175"}),
            "weight_kg": forms.NumberInput(attrs={"placeholder": "例如 68.5"}),
            "age_year":forms.NumberInput(attrs={"placeholder":"例如 20"}),
            "gender":forms.NumberInput(attrs={"placeholder":"老老实实填，别创新"}),
            "exercise_frequency":forms.NumberInput(attrs={"placeholder":"例如 3次/周"}),
            "exercise_time_minutes":forms.NumberInput(attrs={"placeholder":"例如 30分钟/次"}),
            "sleep_hours":forms.NumberInput(attrs={"placeholder":"例如 7小时/天"}),
        }

