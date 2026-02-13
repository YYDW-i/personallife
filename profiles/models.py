from django.conf import settings
from django.db import models

class HealthProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2,null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    age_year=models.IntegerField(null=True,blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"HealthProfile({self.user})"
