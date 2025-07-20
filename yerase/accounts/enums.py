from django.db.models import TextChoices

class Roles(TextChoices):
    SUPER_ADMIN = 'super_admin', 'Super Admin'
    ADMIN = 'admin', 'Admin'
    USER = 'user', 'User'
    INSTRUCTOR = 'instructor', 'Instructor'