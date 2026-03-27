from django.db import models
from django.conf import settings

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='player_profile',
    )
    nickname = models.CharField("昵称", max_length=50, blank=True, default="")
    signature = models.CharField("个性签名", max_length=120, blank=True, default="")
    bio = models.TextField("个人简介", blank=True, default="")
    phone = models.CharField("手机号", max_length=20, blank=True, default="")
    location = models.CharField("所在地", max_length=100, blank=True, default="")
    website = models.URLField("个人网站", blank=True, default="")
    birthday = models.DateField("生日", blank=True, null=True)
    avatar = models.ImageField("头像", upload_to="avatars/", blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} 的资料"