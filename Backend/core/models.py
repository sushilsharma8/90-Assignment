from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now

class UserToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()

    def is_expired(self):
        return now() >= self.expires_at

    def __str__(self):
        return f"Tokens for {self.user.username}"