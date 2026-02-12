from django import forms
from .models import HealthProfile

class HealthProfileForm(forms.ModelForm):
    class Meta:
        model = HealthProfile
        fields = ["height_cm", "weight_kg"]
        widgets = {
            "height_cm": forms.NumberInput(attrs={"placeholder": "例如 175"}),
            "weight_kg": forms.NumberInput(attrs={"placeholder": "例如 68.5"}),
        }

