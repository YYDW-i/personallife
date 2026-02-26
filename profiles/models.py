from django.conf import settings
from django.db import models

class HealthProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2,null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    age_year=models.IntegerField(null=True,blank=True)
    exercise_frequency=models.IntegerField(null=True,blank=True) # 每周运动几次
    exercise_time_minutes=models.IntegerField(null=True,blank=True) # 每次运动多少分钟
    sleep_hours=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True) # 每晚平均睡眠多少小时

    updated_at = models.DateTimeField(auto_now=True)
   
    GENDER_CHOICES = [
        ("M", "男"),
        ("F", "女"),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES,blank=True) 

    ai_summary = models.TextField(blank=True, default="")
    ai_status = models.CharField(max_length=64, blank=True, default="")
    ai_signature = models.CharField(max_length=64, blank=True, default="")  # 用于判断“数据是否变过”
    ai_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"HealthProfile({self.user})"
