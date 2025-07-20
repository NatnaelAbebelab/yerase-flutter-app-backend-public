from django.contrib.auth.models import AbstractUser
from .enums import Roles
from django.db import models

class CustomUser(AbstractUser):

    role = models.CharField(
        max_length=30,
        choices=Roles.choices,
        default=Roles.USER
    )

    def __str__(self):
        return self.username