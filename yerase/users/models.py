from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import datetime
from accounts.models import CustomUser
import uuid

class UsersItemManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class CustomUsers(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='user')
    phone = models.CharField(max_length=20, blank=True, null=True)
    weight = models.CharField(max_length=255, blank=True, default='0')
    height = models.CharField(max_length=255, blank=True, default='0')
    age = models.CharField(max_length=255, blank=True, default='0')
    gender = models.CharField(max_length=255, blank=True, default='-')
    package = models.CharField(max_length=255, blank=True, default='No package available')
    days_left = models.CharField(max_length=255, blank=True, default='0')
    profile = models.CharField(max_length=255, blank=True, default='user-11.jpg')
    otp_code = models.CharField(max_length=255, default='0')
    reset_code = models.CharField(max_length=255, default='0')
    is_deleted = models.BooleanField(default=False)
    created_by = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.CharField(max_length=255, blank=True, null=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.admin.username
    
    objects = UsersItemManager() # Only fetch active items
    all_objects = models.Manager() # Fetch all items

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()