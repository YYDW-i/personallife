from django import forms
from .models import HealthProfile

class HealthProfileForm(forms.ModelForm):
    class Meta:
        model = HealthProfile
        fields = ["height_cm", "weight_kg","age_year","gender"]
        widgets = {
            "height_cm": forms.NumberInput(attrs={"placeholder": "例如 175"}),
            "weight_kg": forms.NumberInput(attrs={"placeholder": "例如 68.5"}),
            "age_year":forms.NumberInput(attrs={"placeholder":"例如 20"}),
            "gender":forms.NumberInput(attrs={"placeholder":"老老实实填，别创新"})
        }

