from django.contrib.auth import get_user_model
from django.db.utils import OperationalError
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import date
from accounts.models import CustomUser
from .models import CustomAdmin, CourseCategory
import logging

User = get_user_model()
logger = logging.getLogger(__name__)
today = date.today()

def create_default_users():
    default_users = [
        {
            "first_name": "Developer",
            "last_name": "",
            "username": "developer@gmail.com",
            "email": "developer@gmail.com",
            "role": "super_admin",
            "phone": "0911000000",
            "is_superuser": False,
            "is_staff": True,
            "is_active": True,
            "password": "6imU6U*b"
        }
    ]

    for user_data in default_users:
        try:
            if not User.objects.filter(username=user_data["username"]).exists():
                user = CustomUser.objects.create(
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    username=user_data["username"],
                    email=user_data["email"],
                    role=user_data["role"],
                    password=make_password(user_data["password"]),
                )
                if user_data.get("is_superuser"):
                    user.is_superuser = True
                if user_data.get("is_staff"):
                    user.is_staff = True
                if user_data.get("is_active"):
                    user.is_active = True
                user.save()

                admin = CustomAdmin.objects.create(
                    admin=user,
                    phone=user_data["phone"],
                    otp_code = "1",
                    profile = "",
                    created_by="startup",
                    created_at=today,
                    updated_by="startup",
                    updated_at=today,
                    record_time=timezone.now()
                )
                admin.save()
        except OperationalError as e:
            # This handles the case when DB isn't ready yet during migrations
            pass
        except Exception as e:
            logger.error("Error occurred while creating default users: %s", e)
            return

def create_default_course_category():
    default_categories = [
        {
            "name": "General",
            "description": "This is general category",
            "color": "#000000",
            "icon": "",
        }
    ]

    for category_data in default_categories:
        try:
            if not CourseCategory.objects.filter(name=category_data["name"].lower()).exists():
                category = CourseCategory.objects.create(
                    name=category_data["name"],
                    description=category_data["description"],
                    color=category_data["color"],
                    icon=category_data["icon"]
                )
                category.save()
                
        except OperationalError as e:
            # This handles the case when DB isn't ready yet during migrations
            pass
        except Exception as e:
            logger.error("Error occurred while creating default category: %s", e)
            return
