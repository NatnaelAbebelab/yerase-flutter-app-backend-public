import logging
import os
import random
import requests
import secrets
import string
from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q, F
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from pydub import AudioSegment
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from utils.exceptions import *
from utils.permissions import role_required
from .requestSerializers import *
from .services.pagination import *
from .services.roles import get_user_role
from .services.validations import *
from .utility.token import get_tokens_for_user

# Create your views here.
logger = logging.getLogger(__name__)
today = date.today()
User = get_user_model()
ROLE_CHOICES = ["super_admin", "weight_man", "purchaser", "inspector", "purchase_head", "supervisor", "factory_manager", "finance", "manager"]

"""
This is views for activities or tasks performed by admins
"""

def generate_temp_password(length):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for _ in range(length))
def generate_otp():
    return str(random.randint(100000, 999999))

class AdminLoginView(APIView):
    """
    Class-based views for login
    """
    @extend_schema(
        tags=["Admin Account"],
        request=AdminLoginSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AdminLoginSerializer(data=request.data) # DRF automatically parses the request body on every request that has a body
        
        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            email = serializer.validated_data["email"].lower()
            password = serializer.validated_data["password"]
        
            # Validation
            validator = AdminAccountDataValidator(serializer.validated_data, fields=["email", "password"])
            if not validator.is_valid():
                raise ValidationException(validator.errors)
            
            user = get_object_or_404(CustomUser.objects, username=email)
            admin = CustomAdmin.objects.filter(Q(admin=user) & Q(is_deleted=False)).first()
            
            if admin and check_password(password, user.password):
                tokens = get_tokens_for_user(user)
                login(request, user)
                if request.user == user:
                    role = get_user_role(request.user)
                    return JsonResponse({"result": "success", "message": "Admin logged in successfully", "content": {"logged_user": user.username, "tokens": tokens, "role": role}}, status=status.HTTP_200_OK)
            raise InvalidAdminCredentialsException("Admin account not found")
        
        except (BaseClassSerializerException, ValidationException, InvalidAdminCredentialsException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404 as e:
            return JsonResponse({"result": "error", "message": "Admin not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while login admin: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while sign in admin."}, status=status.HTTP_400_BAD_REQUEST)

class AdminLogoutView(APIView):
    """
    Class-based to handle logout
    """
    @extend_schema(
        tags=["Admin Account"],
        responses={200: dict}
    )
    def post(self, request):
        logout(request)
        return JsonResponse({"result": "success", "message": "You logged out."}, staticmethod=status.HTTP_200_OK)
    
@permission_classes([IsAuthenticated, role_required(["super_admin"])])
class AdminAccountView(APIView):
    """
    Class-based view to manage admins accounts (CRUD on accounts)
    """
    @extend_schema(
        tags=["Admin Account"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            users = CustomAdmin.objects.select_related("admin").exclude(admin__role="super_admin").all().order_by("-record_time")
            
            if not users.exists():
                raise Http404

            paginator = AdminsDataPagination()
            admins = paginator.paginate_admins(request, users)
            return JsonResponse({"result": "success", "message": "Admins list", "content": admins.data}, status=status.HTTP_200_OK)
        
        except Http404:
            return JsonResponse({"result": "error", "message": "Admins users not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching admins: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching admins."}, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        tags=["Admin Account"],
        request=AdminAccountCreateSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AdminAccountCreateSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            fname = serializer.validated_data["fname"]
            lname = serializer.validated_data["lname"]
            email = serializer.validated_data["email"].lower()
            phone = serializer.validated_data["phone"]
            role = serializer.validated_data["role"].lower()
        
            # Validation
            validator = AdminAccountDataValidator(serializer.validated_data, fields=["fname", "lname", "email", "phone", "role"], empty_validation=True, null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)
            
            if CustomUser.objects.filter(username=email).exists():
                raise EmailDuplicationException("Email is already used.")
            
            temp_password = generate_temp_password(8)
            otp_code = '0'
            
            while 1 :
                otp_code = generate_otp()
                if CustomAdmin.objects.filter(otp_code=otp_code).count() > 0 :
                    continue
                else : break
            
            user = CustomUser.objects.create(
                first_name=fname,
                last_name=lname,
                username=email,
                email=email,
                role=role,
                password=make_password(temp_password),
            )
            user.save()
            
            admin = CustomAdmin.objects.create(
                admin=user,
                phone=phone,
                otp_code = otp_code,
                profile = "",
                created_by="super_admin",
                created_at=today,
                updated_by="startup",
                updated_at=today,
                record_time=timezone.now()
            )
            admin.save()
            
            # send email
            context = {
                'fname' : fname.capitalize(),
                'lname' : lname.capitalize(),
                'email' : email,
                'otp_code' : otp_code
            }
            template = get_template('add-user-email-template.html')
            message_content = template.render(context)
            subject = 'Reset Your Password'
            message = message_content
            email = EmailMessage(subject, message, 'natnaelabebelab@gmail.com', [email])
            email.content_subtype = 'html'  # Specify that the email content is HTML
            email.send()
            return JsonResponse({"result": "success", "message": "Admin created successfully"}, status=status.HTTP_200_OK)
        
        except (BaseClassSerializerException, ValidationException, EmailDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Exception as e:
            logger.error("Error occurred while registering user: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while registering admin."}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Admin Account"],
        request=AdminAccountPatchSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = AdminAccountPatchSerializer(data=request.data)
        
        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)
            
            _id = serializer.validated_data["_id"]
            fname = serializer.validated_data["fname"]
            lname = serializer.validated_data["lname"]
            email = serializer.validated_data["email"].lower()
            phone = serializer.validated_data["phone"]
            role = serializer.validated_data["role"].lower()
            
            
            if not _id:
                raise UUIDException("Record is not found.")
            # Value Validation
            validator = AdminAccountDataValidator(serializer.validated_data, fields=["fname", "lname", "email", "phone", "role"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)
            
            _user = CustomUser.objects.filter(username=email).first()
            if _user and CustomAdmin.objects.filter(~Q(_id=_id) & Q(admin=_user.id)).exists():
                raise EmailDuplicationException("Email is already used.")
            
            admin = get_object_or_404(CustomAdmin.objects, _id=_id)
            user = get_object_or_404(CustomUser.objects, username=admin.admin)
            
            if fname:
                user.first_name = fname
            if lname:
                user.last_name = lname
            if email:
                user.username = email
                user.email = email
            if role:
                user.role = role

            user.save()
            
            if phone:
                admin.phone = phone
            admin.save()
            return JsonResponse({"result": "success", "message": "Admin account is updated successfully"}, status=status.HTTP_200_OK)
        except (BaseClassSerializerException, UUIDException, ValidationException, EmailDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Admin account not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating admin account: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating admin account"}, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        tags=["Admin Account"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record not found.")
            
            admin = get_object_or_404(CustomAdmin.objects, _id=_id)
            admin.delete()
            return JsonResponse({"result": "success", "message": "Admin account is deleted successfully."}, status=status.HTTP_200_OK)
        except (UUIDException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Admin record not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting admin: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting admin"}, status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class ResetPasswordView(APIView):
    """
    Class-based view to change profile settings
    """
    @extend_schema(
        tags=["Admin Account"],
        request=ResetPasswordSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        
        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)
            
            password = serializer.validated_data["password"]
            otp_code = serializer.validated_data["otp_code"]
        
            # Value Validation
            validator = AdminAccountDataValidator(serializer.validated_data, fields=["password"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)
            
            admin = get_object_or_404(CustomAdmin.objects, otp_code=otp_code)
            user = get_object_or_404(CustomUser.objects, id=admin.admin)
            
            user.password = make_password(password)
            user.save()
            return JsonResponse({"result": "success", "message": "You have reset your password successfully."}, status=status.HTTP_200_OK)
        
        except (BaseClassSerializerException, ValidationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "OTP code is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while resetting password: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while resetting password"}, status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class AdminUpdateProfileView(APIView):
    """
    Class-based view to update admin profile
    """
    @extend_schema(
        tags=["Admin Account"],
        request=AdminUpdateProfileInfoSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = AdminUpdateProfileInfoSerializer(data=request.data)
        
        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)
            
            profile = serializer.validated_data["profile"]
            fname = serializer.validated_data["fname"]
            lname = serializer.validated_data["lname"]
            email = serializer.validated_data["email"].lower()
            phone = serializer.validated_data["phone"]
        
            # Value Validation
            validator = AdminAccountDataValidator(serializer.validated_data, fields=["fname", "lname", "email","phone"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)
            
            current_user = get_object_or_404(CustomUser.objects, username=request.user)
            current_admin = get_object_or_404(CustomAdmin.objects, admin=current_user.id)

            if CustomUser.objects.filter(~Q(id=current_user.id) & Q(email=email)).exists():
                raise EmailDuplicationException("Email is already used.")
            
            file_name = str(uuid.uuid4())
            if profile is not None :
                file_path = os.path.join(settings.MEDIA_ROOT, 'admin/admins-profile', file_name + '.' + profile.name.split('.')[-1])
                # Ensure directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                # Save file manually
                with open(file_path, 'wb+') as destination:
                    for chunk in profile.chunks():
                        destination.write(chunk)
                current_admin.profile = file_name + '.' + profile.name.split('.')[-1]
            
            if fname:
                current_user.first_name = fname
            if lname:
                current_user.last_name = lname
            if email:
                current_user.username = email
                current_user.email = email
            current_user.save()

            if phone:
                current_admin.phone = phone
            current_admin.save()
            
            return JsonResponse({"result": "success", "message": "Your profile information is updated successfully."}, status=status.HTTP_200_OK)
        
        except (BaseClassSerializerException, ValidationException, EmailDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Your account is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating profile: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating profile"}, status=status.HTTP_400_BAD_REQUEST)


@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class AdminChangePasswordView(APIView):
    """
    Class view to change password
    """
    @extend_schema(
        tags=["Admin Account"],
        request=AdminChangePasswordSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = AdminChangePasswordSerializer(data=request.data)
        
        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)
            
            old_password = serializer.validated_data["old_password"]
            new_password = serializer.validated_data["new_password"]
        
            # Value Validation
            validator = AdminAccountDataValidator(serializer.validated_data, fields=["password"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            current_user = get_object_or_404(CustomUser.objects, username=request.user)
            
            if not check_password(old_password, current_user.password) :
                raise WrongPasswordException("Current password is invalid.")
            
            current_user.password = make_password(new_password)
            current_user.save()
            
            return JsonResponse({"result": "success", "message": "Your password is changed successfully."}, status=status.HTTP_200_OK)
        
        except (BaseClassSerializerException, ValidationException, WrongPasswordException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Your account is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while changing password: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while changing password"}, status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class AdminRecoverPasswordView(APIView):
    """
    Class view to recover password
    """
    @extend_schema(
        tags=["Admin Account"],
        request=AdminRecoverPasswordSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AdminRecoverPasswordSerializer(data=request.data)
        
        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)
            
            email = serializer.validated_data["email"].lower()
        
            # Value Validation
            validator = AdminAccountDataValidator(serializer.validated_data, fields=["email"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)
            
            current_user = get_object_or_404(CustomUser.objects, username=request.user)
            current_admin = get_object_or_404(CustomAdmin.objects, admin=current_user.id)
            
            if CustomUser.objects.filter(~Q(id=current_user.id) & Q(email=email)).exists():
                raise EmailDuplicationException("Email is already used.")
            
            temp_password = generate_temp_password(8)
            otp_code = '0'
            while 1 :
                otp_code = generate_otp()
                if CustomAdmin.objects.filter(otp_code=otp_code).count() > 0 :
                    continue
                else : break
            
            current_admin.otp_code = otp_code
            current_admin.save()
            
            current_user.password = make_password(temp_password)
            current_user.save()
            
            return JsonResponse({"result": "success", "message": "You've recovered your password successfully."}, status=status.HTTP_200_OK)
        
        except (BaseClassSerializerException, ValidationException, EmailDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Your account is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while recovering password: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while recovering password"}, status=status.HTTP_400_BAD_REQUEST)

"""
===============> Courses Class Based Views <=====================
"""
@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class CourseCategoryView(APIView):
    """
    Class-based view for course category
    """
    @extend_schema(
        tags=["Course Category"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            categories = CourseCategory.objects.all().order_by("-record_time")
            
            if not categories:
                raise Http404

            paginator = CourseDataPagination()
            categories_list = paginator.paginate_course_categories(request, categories)

            return JsonResponse({"result": "success", "message": "Course categories list", "content": categories_list.data}, status=status.HTTP_200_OK)
        
        except Http404:
            return JsonResponse({"result": "error", "message": "Course categories is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching course categories: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching course categories."}, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        tags=["Course Category"],
        request=AddCourseCategorySerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddCourseCategorySerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            name = serializer.validated_data["name"].lower()
            description = serializer.validated_data["description"]
            color = serializer.validated_data["color"]
            icon = serializer.validated_data["icon"]
        
            # Value Validation
            validator = CourseCategoryDataValidator(serializer.validated_data, fields=["name", "color", "icon"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)
        
            if CourseCategory.objects.filter(name=name).exists():
                raise CategoryNameDuplicationException("Course category name is already used.")
            
            file_name = str(uuid.uuid4())
            if icon is not None :
                file_path = os.path.join(settings.MEDIA_ROOT, 'courses/category', file_name + '.' + icon.name.split('.')[-1])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'wb+') as destination:
                    for chunk in icon.chunks():
                        destination.write(chunk)
                file_name = file_name + '.' + icon.name.split('.')[-1]
            
            category = CourseCategory.objects.create(
                name=name,
                description=description,
                color=color,
                icon=file_name,
                created_on=today,
                updated_on=today
            )
            category.save()
            
            return JsonResponse({"result": "success", "message": "Course category is created successfully."}, status=status.HTTP_200_OK)
        
        except (BaseClassSerializerException, ValidationException, CategoryNameDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Exception as e:
            logger.error("Error occurred while creating course category: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating course category."}, status=status.HTTP_400_BAD_REQUEST)
            
    @extend_schema(
        tags=["Course Category"],
        request=UpdateCourseCategorySerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdateCourseCategorySerializer(data=request.data)
        
        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            name = serializer.validated_data["name"].lower()
            description = serializer.validated_data["description"]
            color = serializer.validated_data["color"]
            icon = serializer.validated_data["icon"]
            
            # Value Validation
            validator = CourseCategoryDataValidator(serializer.validated_data, fields=["name", "color", "icon"])
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            category = get_object_or_404(CourseCategory.objects, _id=_id)
            
            if CourseCategory.objects.filter(~Q(_id=category._id) & Q(name=name)).exists():
                raise CategoryNameDuplicationException("Course category name is already used.")
            
            file_name = str(uuid.uuid4())
            if icon is not None :
                file_path = os.path.join(settings.MEDIA_ROOT, 'courses/category', file_name + '.' + icon.name.split('.')[-1])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'wb+') as destination:
                    for chunk in icon.chunks():
                        destination.write(chunk)
                file_name = file_name + '.' + icon.name.split('.')[-1]
            
            if name:
                category.name = name
            if description:
                category.description = description
            if color:
                category.color = color
            category.icon = file_name
            category.record_time = timezone.now()
            category.save()
            
            return JsonResponse({"result": "success", "message": "Course category is updated successfully."}, status=status.HTTP_200_OK)
        
        except (BaseClassSerializerException, ValidationException, CategoryNameDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Category record is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating course category: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating course category."}, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        tags=["Course Category"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")
            
            category = get_object_or_404(CourseCategory.objects, _id=_id)
            category.delete()
            return JsonResponse({"result": "success", "message": "Course category is deleted successfully."}, status=status.HTTP_200_OK)
        except (UUIDException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Course category record not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting course category: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting course category"}, status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class CourseView(APIView):
    """
    Class-based views for course
    """
    @extend_schema(
        tags=["Course"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            courses = Course.objects.all().order_by("-record_time")
            
            if not courses:
                raise Http404

            paginator = CourseDataPagination()
            courses_list = paginator.paginate_courses(request, courses)
            
            return JsonResponse({"result": "success", "message": "Courses list", "content": courses_list.data}, status=status.HTTP_200_OK)
        
        except Http404:
            return JsonResponse({"result": "error", "message": "Courses is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching courses: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching courses."}, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        tags=["Course"],
        request=AddCourseSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddCourseSerializer(data=request.data)
        
        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            title = serializer.validated_data["title"].lower()
            category = serializer.validated_data["category"]
            thumbnail = serializer.validated_data["thumbnail"]
            overview = serializer.validated_data["overview"]
            description = serializer.validated_data["description"]
            objectives =  serializer.validated_data["objectives"]
            intro = serializer.validated_data["intro"]
            level = serializer.validated_data["level"]
            certificate = serializer.validated_data["certificate"].lower()
            language = serializer.validated_data["language"].lower()
            # Value Validation
            validator = CourseDataValidator(serializer.validated_data, fields=["title", "thumbnail", "overview", "description", "intro", "level", "certificate", "language"], empty_validation=True, null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            category = get_object_or_404(CourseCategory.objects, _id=category)
            
            if Course.objects.filter(title=title).exists():
                raise TitleDuplicationException("Course title is already used.")
            
            file_name = str(uuid.uuid4())
            if thumbnail is not None :
                file_path = os.path.join(settings.MEDIA_ROOT, "course/thumbnail", file_name + '.' + thumbnail.name.split('.')[-1])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'wb+') as destination:
                    for chunk in thumbnail.chunks():
                        destination.write(chunk)
                file_name = file_name + '.' + thumbnail.name.split('.')[-1]
        
            course = Course.objects.create(
                title=title,
                category=category,
                thumbnail=file_name,
                overview=overview,
                description=description,
                objectives=objectives,
                intro=intro,
                level=level,
                is_certificated=certificate,
                language=language,
                created_at=today,
                updated_at=today
            )
            course.save()
            
            # update course category
            category.assigned_course = int(category.assigned_course) + 1
            category.save()
            
            return JsonResponse({"result": "success", "message": "Course is added successfully."}, status=status.HTTP_200_OK)
        
        except (BaseClassSerializerException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Category is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating course: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating course"}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Course"],
        request=UpdateCourseSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdateCourseSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            title = serializer.validated_data["title"].lower()
            category = serializer.validated_data["category"]
            thumbnail = serializer.validated_data["thumbnail"]
            overview = serializer.validated_data["overview"]
            description = serializer.validated_data["description"]
            objectives =  serializer.validated_data["objectives"]
            intro = serializer.validated_data["intro"]
            level = serializer.validated_data["level"]
            certificate = serializer.validated_data["certificate"].lower()
            language = serializer.validated_data["language"].lower()

            if not _id:
                raise UUIDException("Record is not found.")

            # Value Validation
            validator = CourseDataValidator(serializer.validated_data, fields=["title", "thumbnail", "overview", "description", "objectives", "intro", "level", "certificate", "language"])
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            if category:
                category = get_object_or_404(CourseCategory.objects, _id=category)

            if Course.objects.filter(~Q(_id=_id) & Q(title=title)).exists():
                raise TitleDuplicationException("Course title is already used.")

            course = get_object_or_404(Course.objects, _id=_id)

            file_name = str(uuid.uuid4())
            if thumbnail:
                file_path = os.path.join(settings.MEDIA_ROOT, "course/thumbnail", file_name + '.' + thumbnail.name.split('.')[-1])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'wb+') as destination:
                    for chunk in thumbnail.chunks():
                        destination.write(chunk)
                file_name = file_name + '.' + thumbnail.name.split('.')[-1]

            if title:
                course.title = title
            if category:
                pre_category = course.category
                if category != pre_category:
                    _assigned_pre_category = CourseCategory.objects.get(_id=pre_category)
                    _assigned_pre_category.assigned_course = int(_assigned_pre_category.assigned_course) - 1
                    _assigned_pre_category.save()

                    new_category = CourseCategory.objects.get(_id=category)
                    new_category.assigned_course = int(new_category.assigned_course) + 1
                    new_category.save()
                course.category = category
            if thumbnail:
                course.thumbnail = file_name
            if overview:
                course.overview = overview
            if description:
                course.description = description
            if objectives:
                course.objectives = objectives
            if intro:
                course.intro = intro
            if level:
                course.level = level
            if certificate:
                course.is_certificated = certificate
            if language:
                course.language = language
            course.updated_at = timezone.now()
            course.record_time = timezone.now()
            course.save()

            return  JsonResponse({"result": "success", "message": "Course is updated successfully."}, status=status.HTTP_200_OK)

        except (UUIDException, BaseClassSerializerException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Course record not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating course: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating course"}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Course"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            course = get_object_or_404(Course.objects, _id=_id)
            course.delete()

            return JsonResponse({"result": "success", "message": "Course is deleted successfully."}, status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Course record not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting course: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting course"}, status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class CourseLessonView(APIView):
    """
    Course lesson class-based view
    """
    @extend_schema(
        tags=["Course Lesson"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            lessons = CourseLesson.objects.all().order_by("-record_time")

            if not lessons:
                raise Http404

            paginator = CourseLessonDataPagination()
            lessons_list = paginator.paginate_course_lessons(request, lessons)

            return JsonResponse({"result": "success", "message": "Course lessons list", "content": lessons_list.data}, status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Course lessons is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching course lessons: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching course lessons."}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Course Lesson"],
        request=AddCourseLessonSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddCourseLessonSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            title = serializer.validated_data["title"]
            course = serializer.validated_data["course"]
            description = serializer.validated_data["description"]
            thumbnail = serializer.validated_data["thumbnail"]
            video_id = serializer.validated_data["video_id"]

            # Value Validation
            validator = CourseLessonDataValidator(serializer.validated_data, fields=["title", "course", "description", "thumbnail", "video_id"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            # Get duration of the video
            oembed_url = f"https://vimeo.com/api/oembed.json?url=https://player.vimeo.com/video/{video_id}"
            response = requests.get(oembed_url)
            duration = 0
            if response.status_code == 200:
                data = response.json()
                duration = data.get("duration", 0)
            duration_validation = CourseLessonDataValidator(serializer.validated_data, fields=["duration"], null_validation=True)
            if not duration_validation.is_valid():
                raise ValidationException(duration_validation.errors)

            with transaction.atomic():
                # user = get_object_or_404(CourseCategory.objects, _id=category)
                user = 2
                if CourseLesson.objects.filter(title=title.lower()).exists():
                    raise TitleDuplicationException("Lesson title is already used.")

                course_ = Course.objects.select_for_update().filter(_id=course).first()
                if not course_:
                    raise Http404("Course not found.")

                # Upload thumbnail
                file_name = str(uuid.uuid4())
                if thumbnail is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "course/lesson",
                                             file_name + '.' + thumbnail.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in thumbnail.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + thumbnail.name.split('.')[-1]

                course_lesson = CourseLesson.objects.create(
                    title=title.lower(),
                    course=course,
                    thumbnail=file_name,
                    duration=duration,
                    description=description,
                    video_id=video_id,
                    created_at=today,
                    updated_at=today
                )
                course_lesson.save()

                # Update course metadata
                course_.lesson_count = F('lesson_count') + 1
                course_.total_duration = F('total_duration') + duration
                course_.save(update_fields=["lesson_count", "total_duration"])
                course_.refresh_from_db(fields=["lesson_count", "total_duration"])

                return JsonResponse({"result": "success", "message": "Course lesson is added successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating course lesson: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating course lesson"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Course Lesson"],
        request=UpdateCourseLessonSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdateCourseLessonSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            title = serializer.validated_data["title"]
            course = serializer.validated_data["course"]
            description = serializer.validated_data["description"]
            thumbnail = serializer.validated_data["thumbnail"]
            video_id = serializer.validated_data["video_id"]

            if not _id:
                raise UUIDException("Record is not found.")

            # Value Validation
            validator = CourseLessonDataValidator(serializer.validated_data,
                                                  fields=["title", "course", "description", "thumbnail", "video_id"])
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                lesson = CourseLesson.objects.select_for_update().filter(_id=_id).first()
                if not lesson:
                    raise Http404("Lesson not found.")

                if CourseLesson.objects.filter(Q(title=title.lower()) & ~Q(_id=_id)).exists():
                    raise TitleDuplicationException("Lesson title is already used.")

                duration = int(lesson.duration)
                if video_id:
                    # Get duration of the video
                    oembed_url = f"https://vimeo.com/api/oembed.json?url=https://player.vimeo.com/video/{video_id}"
                    response = requests.get(oembed_url)
                    if response.status_code == 200:
                        data = response.json()
                        duration = data.get("duration", 0)
                    duration_validation = CourseLessonDataValidator(serializer.validated_data, fields=["duration"],
                                                                    null_validation=True)
                    if not duration_validation.is_valid():
                        raise ValidationException(duration_validation.errors)
                    lesson.video_id = video_id

                pre_course = get_object_or_404(Course.objects, _id=lesson.course)
                if course:
                    new_course = get_object_or_404(Course.objects, _id=course)

                    pre_course.lesson_count = F("lesson_count") - 1
                    pre_course.total_duration = F("total_duration") - int(lesson.duration)
                    pre_course.save(update_fields=["lesson_count", "total_duration"])

                    # Add to new course
                    new_course.lesson_count = F("lesson_count") + 1
                    new_course.total_duration = F("total_duration") + duration
                    new_course.save(update_fields=["lesson_count", "total_duration"])

                    # Assign new course
                    lesson.course = course

                # Upload thumbnail
                file_name = str(uuid.uuid4())
                if thumbnail is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "course/lesson",
                                             file_name + '.' + thumbnail.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in thumbnail.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + thumbnail.name.split('.')[-1]
                    lesson.thumbnail = file_name

                lesson.duration = duration
                if title:
                    lesson.title = title.lower()
                if description:
                    lesson.description = description
                lesson.save()

                return  JsonResponse({"result": "success", "message": "Course lesson is updated successfully."}, status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating course lesson: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating course lesson"}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Course Lesson"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            lesson = get_object_or_404(CourseLesson.objects, _id=_id)
            lesson.delete()

            return JsonResponse({"result": "success", "message": "Course lesson is deleted successfully."},
                                status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Course lesson record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting course lesson: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting course lesson"},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class CourseReviewView(APIView):
    """
    Course review class-based view
    """
    @extend_schema(
        tags=["Course Review"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            course_reviews = CourseReview.objects.all().order_by("-record_time")

            if not course_reviews:
                raise Http404

            paginator = CourseReviewDataPagination()
            courses_list = paginator.paginate_course_reviews(request, course_reviews)

            return JsonResponse({"result": "success", "message": "Course reviews list", "content": courses_list.data}, status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Course review is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching course reviews: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching course reviews."}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Course Review"],
        request=AddCourseReviewSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddCourseReviewSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            user = serializer.validated_data["user"]
            course = serializer.validated_data["course"]
            rate = serializer.validated_data["rate"]
            review = serializer.validated_data["review"]

            # Value Validation
            validator = CourseReviewDataValidator(serializer.validated_data, fields=["user", "course", "rate", "review"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            #user = get_object_or_404(CourseCategory.objects, _id=category)
            user = 2

            course = get_object_or_404(Course.objects, _id=course)

            course_review = CourseReview.objects.create(
                active_user=user,
                course=course,
                rate=rate,
                review=review,
                created_at=today,
                updated_at=today
            )
            course_review.save()

            return JsonResponse({"result": "success", "message": "Course review is added successfully."}, status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating course review: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating course review"}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Course Review"],
        request=UpdateCourseReviewSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdateCourseReviewSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            user = serializer.validated_data["user"]
            course = serializer.validated_data["course"]
            rate = serializer.validated_data["rate"]
            review = serializer.validated_data["review"]

            if not _id:
                raise UUIDException("Record is not found.")

            # Value Validation
            validator = CourseReviewDataValidator(serializer.validated_data, fields=["user", "course", "rate", "review"])
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            if course:
                course = get_object_or_404(Course.objects, _id=course)

            course_review = get_object_or_404(CourseReview.objects, _id=_id)

            if user:
                course_review.active_user = user
            if course:
                course_review.course = course
            if rate:
                course_review.rate = rate
            if review:
                course_review.review = review
            course_review.updated_at = timezone.now()
            course_review.record_time = timezone.now()
            course_review.save()

            return  JsonResponse({"result": "success", "message": "Course review is updated successfully."}, status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException, ValidationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating course review: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating course review"}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Course Review"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            course_review = get_object_or_404(CourseReview.objects, _id=_id)
            course_review.delete()

            return JsonResponse({"result": "success", "message": "Course review is deleted successfully."}, status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Course review record not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting course review: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting course review"}, status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class MealPlanView(APIView):
    """
    Meal plan class based view
    """

    @extend_schema(
        tags=["Meal Plan"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            meals = MealPlan.objects.all().order_by("-record_time")

            if not meals:
                raise Http404

            paginator = MealPlanDataPagination()
            meals_list = paginator.paginate_meal_plan(request, meals)

            return JsonResponse({"result": "success", "message": "Meal plans list", "content": meals_list.data},
                                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Meal plans are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching meal plans: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching meal plans."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Meal Plan"],
        request=AddMealPlanSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddMealPlanSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            name = serializer.validated_data["name"]
            overview = serializer.validated_data["overview"]
            description = serializer.validated_data["description"]
            thumbnail = serializer.validated_data["thumbnail"]
            course = serializer.validated_data["course"]
            intro = serializer.validated_data["intro"]

            # Value Validation
            validator = MealPlanDataValidator(serializer.validated_data,
                                                  fields=["name", "overview", "description", "thumbnail", "course", "intro"],
                                                  null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                if MealPlan.objects.filter(name=name.lower()).exists():
                    raise TitleDuplicationException("Meal plan name is already used.")

                course_ = Course.objects.select_for_update().filter(_id=course).first()
                if not course_:
                    raise Http404("Course not found.")

                # Upload thumbnail
                file_name = str(uuid.uuid4())
                if thumbnail is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "meal/plan",
                                             file_name + '.' + thumbnail.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in thumbnail.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + thumbnail.name.split('.')[-1]

                meal = MealPlan.objects.create(
                    name=name.lower(),
                    overview=overview,
                    description=description,
                    thumbnail=file_name,
                    course=course,
                    intro=intro,
                    created_at=today,
                    updated_at=today
                )
                meal.save()

                return JsonResponse({"result": "success", "message": "Meal plan is added successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating meal plan: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating meal Plan"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Meal Plan"],
        request=UpdateMealPlanSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdateMealPlanSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            name = serializer.validated_data["name"]
            overview = serializer.validated_data["overview"]
            description = serializer.validated_data["description"]
            thumbnail = serializer.validated_data["thumbnail"]
            course = serializer.validated_data["course"]
            intro = serializer.validated_data["intro"]

            if not _id:
                raise UUIDException("Record is not found.")

            # Value Validation
            validator = MealPlanDataValidator(serializer.validated_data,
                                              fields=["name", "overview", "description", "thumbnail", "course", "intro"])
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                meal = MealPlan.objects.select_for_update().filter(_id=_id).first()
                if not meal:
                    raise Http404("Meal plan not found.")

                if MealPlan.objects.filter(Q(name=name.lower()) & ~Q(_id=_id)).exists():
                    raise TitleDuplicationException("Meal plan name is already used.")

                # Upload thumbnail
                file_name = str(uuid.uuid4())
                if thumbnail is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "meal/plan",
                                             file_name + '.' + thumbnail.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in thumbnail.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + thumbnail.name.split('.')[-1]
                    meal.thumbnail = file_name

                if name:
                    meal.name = name.lower()
                if overview:
                    meal.overview = overview
                if description:
                    meal.description = description
                if course:
                    meal.course = course
                if intro:
                    meal.intro = intro
                meal.save()

                return JsonResponse({"result": "success", "message": "Meal plan is updated successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating meal plan: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating meal plan"},
                            status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Meal Plan"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            meal = get_object_or_404(MealPlan.objects, _id=_id)
            meal.delete()

            return JsonResponse({"result": "success", "message": "Meal plan is deleted successfully."},
                                status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Meal plan record not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting meal plan: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting meal plan"},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class MealPlanRecipeView(APIView):
    """
    Meal plan recipe class based view
    """

    @extend_schema(
        tags=["Meal Recipe"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            recipes = MealPlanRecipe.objects.all().order_by("-record_time")

            if not recipes:
                raise Http404

            paginator = MealPlanRecipeDataPagination()
            recipes_list = paginator.paginate_meal_recipe(request, recipes)

            return JsonResponse({"result": "success", "message": "Meal plan recipes list", "content": recipes_list.data},
                                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Meal plan recipes are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching meal plan recipes: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching meal plan recipes."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Meal Recipe"],
        request=AddMealPlanRecipeSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddMealPlanRecipeSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            name = serializer.validated_data["name"]
            plan = serializer.validated_data["plan"]
            description = serializer.validated_data["description"]
            thumbnail = serializer.validated_data["thumbnail"]
            video = serializer.validated_data["video"]

            # Value Validation
            validator = MealPlanRecipeValidator(serializer.validated_data,
                                              fields=["name", "plan", "description", "thumbnail", "video"],
                                              null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            # Get duration of the video
            oembed_url = f"https://vimeo.com/api/oembed.json?url=https://player.vimeo.com/video/{video}"
            response = requests.get(oembed_url)
            duration = 0
            if response.status_code == 200:
                data = response.json()
                duration = data.get("duration", 0)
            duration_validation = MealPlanRecipeValidator(serializer.validated_data, fields=["duration"],
                                                            null_validation=True)
            if not duration_validation.is_valid():
                raise ValidationException(duration_validation.errors)

            with transaction.atomic():
                if MealPlanRecipe.objects.filter(name=name.lower()).exists():
                    raise TitleDuplicationException("Meal recipe name is already used.")

                meal = MealPlan.objects.select_for_update().filter(_id=plan).first()
                if not meal:
                    raise Http404("Meal plan not found.")

                # Upload thumbnail
                file_name = str(uuid.uuid4())
                if thumbnail is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "meal/recipe-thumbnail",
                                             file_name + '.' + thumbnail.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in thumbnail.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + thumbnail.name.split('.')[-1]

                recipe = MealPlanRecipe.objects.create(
                    name=name.lower(),
                    meal=plan,
                    thumbnail=file_name,
                    duration=duration,
                    description=description,
                    video_link=video,
                    created_at=today,
                    updated_at=today
                )
                recipe.save()

                # Update meal plan metadata
                meal.recipe_count = F("recipe_count") + 1
                meal.save(update_fields=["recipe_count"])
                meal.refresh_from_db(fields=["recipe_count"])

                return JsonResponse({"result": "success", "message": "Meal plan recipe is added successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating meal plan recipe: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating meal plan recipe"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Meal Recipe"],
        request=UpdateMealPlanRecipeSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdateMealPlanRecipeSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            name = serializer.validated_data["name"]
            plan = serializer.validated_data["plan"]
            description = serializer.validated_data["description"]
            thumbnail = serializer.validated_data["thumbnail"]
            video = serializer.validated_data["video"]

            if not _id:
                raise UUIDException("Record is not found.")

            # Value Validation
            validator = MealPlanRecipeValidator(serializer.validated_data,
                                              fields=["name", "plan", "description", "thumbnail", "video"])
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                recipe = MealPlanRecipe.objects.select_for_update().filter(_id=_id).first()
                if not recipe:
                    raise Http404("Meal recipe not found.")

                if MealPlanRecipe.objects.filter(Q(name=name.lower()) & ~Q(_id=_id)).exists():
                    raise TitleDuplicationException("Meal recipe name is already used.")

                duration = int(recipe.duration)
                if video:
                    # Get duration of the video
                    oembed_url = f"https://vimeo.com/api/oembed.json?url=https://player.vimeo.com/video/{video}"
                    response = requests.get(oembed_url)
                    if response.status_code == 200:
                        data = response.json()
                        duration = data.get("duration", 0)
                    duration_validation = MealPlanRecipeValidator(serializer.validated_data, fields=["duration"],
                                                                    null_validation=True)
                    if not duration_validation.is_valid():
                        raise ValidationException(duration_validation.errors)
                    recipe.video_id = video

                pre_meal = get_object_or_404(MealPlan.objects, _id=recipe.meal)
                if plan:
                    new_meal = get_object_or_404(MealPlan.objects, _id=plan)

                    pre_meal.recipe_count = F("recipe_count") - 1
                    pre_meal.save(update_fields=["recipe_count"])

                    new_meal.recipe_count = F("recipe_count") + 1
                    new_meal.save(update_fields=["lesson_count"])

                    recipe.meal = plan

                # Upload thumbnail
                file_name = str(uuid.uuid4())
                if thumbnail is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "meal/recipe-thumbnail",
                                             file_name + '.' + thumbnail.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in thumbnail.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + thumbnail.name.split('.')[-1]
                    recipe.thumbnail = file_name

                recipe.duration = duration
                if name:
                    recipe.name = name.lower()
                if description:
                    recipe.description = description
                recipe.save()

                return JsonResponse({"result": "success", "message": "Meal plan recipe is updated successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating meal plan recipe: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating meal plan recipe"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Meal Recipe"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            recipe = get_object_or_404(MealPlanRecipe.objects, _id=_id)
            recipe.delete()

            return JsonResponse({"result": "success", "message": "Meal plan is deleted successfully."},
                                status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Meal recipe record not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting meal recipe: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting meal recipe"},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class AudiobookCategoryView(APIView):
    """
    Audiobook class based view
    """
    @extend_schema(
        tags=["Audiobook Category"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            category = AudiobookCategory.objects.all().order_by("-record_time")

            if not category:
                raise Http404

            paginator = AudiobookCategoryDataPagination()
            categories_list = paginator.paginate_audiobook_category(request, category)

            return JsonResponse(
                {"result": "success", "message": "Audiobooks list", "content": categories_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Audiobook are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching audiobook: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching audiobook."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook Category"],
        request=AddAudiobookCategorySerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddAudiobookCategorySerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            name = serializer.validated_data["name"]
            description = serializer.validated_data["description"]
            color = serializer.validated_data["color"]
            icon = serializer.validated_data["icon"]

            # Value Validation
            validator = AudiobookCategoryValidator(serializer.validated_data,
                                                fields=["name", "description", "color", "icon"],
                                                null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                if AudiobookCategory.objects.filter(name=name.lower()).exists():
                    raise TitleDuplicationException("Audiobook name is already used.")

                # Upload icon
                file_name = str(uuid.uuid4())
                if icon is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "audiobook/category",
                                             file_name + '.' + icon.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in icon.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + icon.name.split('.')[-1]

                audiobook_category = AudiobookCategory.objects.create(
                    name=name.lower(),
                    description=description,
                    color=color,
                    icon=file_name,
                    created_at=today,
                    updated_at=today
                )
                audiobook_category.save()

                return JsonResponse({"result": "success", "message": "Audiobook category is added successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating audiobook category: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating audiobook category"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook Category"],
        request=UpdateAudiobookCategorySerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdateAudiobookCategorySerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            name = serializer.validated_data["name"]
            description = serializer.validated_data["description"]
            color = serializer.validated_data["color"]
            icon = serializer.validated_data["icon"]

            if not _id:
                raise UUIDException("Record is not found.")

            # Value Validation
            validator = AudiobookCategoryValidator(serializer.validated_data,
                                                   fields=["name", "description", "color", "icon"])
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                category = AudiobookCategory.objects.select_for_update().filter(_id=_id).first()
                if not category:
                    raise Http404("Audiobook category is not found.")

                if AudiobookCategory.objects.filter(Q(name=name.lower()) & ~Q(_id=_id)).exists():
                    raise TitleDuplicationException("Audiobook category name is already used.")

                # Upload icon
                file_name = str(uuid.uuid4())
                if icon is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "audiobook/category",
                                             file_name + '.' + icon.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in icon.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + icon.name.split('.')[-1]
                    category.icon = file_name

                if name:
                    category.name = name.lower()
                if description:
                    category.description = description
                if color:
                    category.color = color
                category.save()

                return JsonResponse({"result": "success", "message": "Audiobook category is updated successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Audiobook category is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating audiobook category: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating audiobook category"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook Category"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            category = get_object_or_404(AudiobookCategory.objects, _id=_id)
            category.delete()

            return JsonResponse({"result": "success", "message": "Audiobook category is deleted successfully."},
                                status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Audiobook category record not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting audiobook category: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting audiobook category"},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class AudiobookView(APIView):
    """
    Audiobook class based view
    """
    @extend_schema(
        tags=["Audiobook"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            audio_books = Audiobook.objects.all().order_by("-record_time")

            if not audio_books:
                raise Http404

            paginator = AudiobookDataPagination()
            audio_books_list = paginator.paginate_audiobook(request, audio_books)

            return JsonResponse(
                {"result": "success", "message": "Audiobooks list", "content": audio_books_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Audiobooks are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching audiobooks: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching audiobooks."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook"],
        request=AddAudiobookSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddAudiobookSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            title = serializer.validated_data["title"]
            overview = serializer.validated_data["overview"]
            description = serializer.validated_data["description"]
            thumbnail = serializer.validated_data["thumbnail"]
            category = serializer.validated_data["category"]
            audio = serializer.validated_data["audio"]

            # Value Validation
            validator = AudiobookValidator(serializer.validated_data,
                                                fields=["title", "overview", "description", "thumbnail", "category", "audio"],
                                                null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                if Audiobook.objects.filter(title=title.lower()).exists():
                    raise TitleDuplicationException("Audiobook title is already used.")

                audiobook_category = AudiobookCategory.objects.select_for_update().filter(_id=category).first()
                if not audiobook_category:
                    raise Http404("Audiobook category is not found.")

                # Upload thumbnail
                file_name = str(uuid.uuid4())
                if thumbnail is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "audiobook/thumbnail",
                                             file_name + '.' + thumbnail.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in thumbnail.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + thumbnail.name.split('.')[-1]

                #upload audio file
                file_name_audio = str(uuid.uuid4())
                file_name_sliced_audio = str(uuid.uuid4())
                duration = 0
                if audio is not None:
                    # Save original audio file
                    file_ext = audio.name.split('.')[-1]
                    file_path = os.path.join(settings.MEDIA_ROOT, "audiobook/audiobook-audio", f"{file_name_audio}.{file_ext}")
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)

                    with open(file_path, 'wb+') as destination:
                        for chunk in audio.chunks():
                            destination.write(chunk)

                    file_name_audio += f".{file_ext}"
                    # Get audio duration
                    if file_ext == 'mp3':
                        _audio = MP3(file_path)
                        duration = round(_audio.info.length)
                    elif file_ext == 'wav':
                        _audio = WAVE(file_path)
                        duration = round(_audio.info.length)

                    # Slice the audio using pydub (from 50s to 90s)
                    slice_audio_file_path = os.path.join(settings.MEDIA_ROOT, "audiobook/audiobook-sliced-audio",
                                                         f"{file_name_sliced_audio}.{file_ext}")
                    os.makedirs(os.path.dirname(slice_audio_file_path), exist_ok=True)

                    # audio_segment = AudioSegment.from_file(file_path)  # Load the audio
                    # start_ms = 50_000
                    # if len(audio_segment) >= start_ms:
                    #     sliced_audio = audio_segment[50_000:80_000]
                    #     sliced_audio.export(slice_audio_file_path, format=file_ext)
                    # else:
                    #     raise ValueErrorException("Audio file is too short for the specified slicing range.")

                    file_name_sliced_audio += f".{file_ext}"

                audio_book = Audiobook.objects.create(
                    title=title.lower(),
                    category=category,
                    overview=overview,
                    description=description,
                    audio=file_name_audio,
                    sliced_audio=file_name_sliced_audio,
                    duration=duration,
                    thumbnail=file_name,
                    created_at=today,
                    updated_at=today
                )
                audio_book.save()

                # Update audiobook category
                audiobook_category.assigned_audio = F("assigned_audio") + 1
                audiobook_category.save(update_fields=["assigned_audio"])
                audiobook_category.refresh_from_db(fields=["assigned_audio"])

                return JsonResponse({"result": "success", "message": "Audiobook is added successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating audiobook: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating audiobook"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook"],
        request=UpdateAudiobookSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdateAudiobookSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            title = serializer.validated_data["title"]
            overview = serializer.validated_data["overview"]
            description = serializer.validated_data["description"]
            thumbnail = serializer.validated_data["thumbnail"]
            category = serializer.validated_data["category"]
            audio = serializer.validated_data["audio"]

            if not _id:
                raise UUIDException("Record is not found.")

            # Value Validation
            validator = AudiobookValidator(serializer.validated_data,
                                                fields=["title", "overview", "description", "thumbnail", "category", "audio"])
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                audio_book = Audiobook.objects.select_for_update().filter(_id=_id).first()
                if not audio_book:
                    raise Http404("Audiobook is not found.")

                if Audiobook.objects.filter(Q(title=title.lower()) & ~Q(_id=_id)).exists():
                    raise TitleDuplicationException("Audiobook title is already used.")

                # Upload thumbnail
                file_name = str(uuid.uuid4())
                if thumbnail is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "audiobook/thumbnail",
                                             file_name + '.' + thumbnail.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in thumbnail.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + thumbnail.name.split('.')[-1]
                    audio_book.thumbnail = file_name

                # Upload audio file
                if audio is not None:
                    file_name_audio = str(uuid.uuid4())
                    duration = 0
                    file_ext = audio.name.split('.')[-1]
                    file_path = os.path.join(settings.MEDIA_ROOT, "audiobook/audiobook-audio", f"{file_name_audio}.{file_ext}")
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    # Save the uploaded audio file
                    with open(file_path, 'wb+') as destination:
                        for chunk in audio.chunks():
                            destination.write(chunk)
                    file_name_audio += f".{file_ext}"

                    if file_ext == 'mp3':
                        _audio = MP3(file_path)
                        duration = round(_audio.info.length)
                    elif file_ext == 'wav':
                        _audio = WAVE(file_path)
                        duration = round(_audio.info.length)
                    # audio_segment = AudioSegment.from_file(file_path)
                    file_name_sliced_audio = str(uuid.uuid4()) + f".{file_ext}"
                    slice_audio_file_path = os.path.join(settings.MEDIA_ROOT, "audiobook/audiobook-sliced-audio",
                                                         file_name_sliced_audio)
                    os.makedirs(os.path.dirname(slice_audio_file_path), exist_ok=True)

                    # start_ms = 50_000
                    # if len(audio_segment) >= start_ms:
                    #     sliced_audio = audio_segment[50_000:80_000]
                    #     sliced_audio.export(slice_audio_file_path, format=file_ext)
                    # else:
                    #     raise ValueErrorException("Audio file is too short for the specified slicing range.")

                    audio_book.duration = duration
                    audio_book.audio = file_name_audio
                    audio_book.sliced_audio = file_name_sliced_audio

                pre_category = get_object_or_404(AudiobookCategory.objects, _id=audio_book.category)
                if category:
                    new_category = get_object_or_404(AudiobookCategory.objects, _id=category)

                    pre_category.assigned_audio = F("assigned_audio") - 1
                    pre_category.save(update_fields=["assigned_audio"])

                    new_category.assigned_audio = F("assigned_audio") + 1
                    new_category.save(update_fields=["assigned_audio"])

                    audio_book.category = category

                if title != '':
                    audio_book.title = title.lower()
                if overview != '':
                    audio_book.overview = overview
                if description != '':
                    audio_book.description = description
                audio_book.save()

                return JsonResponse({"result": "success", "message": "Audiobook is updated successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException, ValidationException, TitleDuplicationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating audiobook: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating audiobook"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            audio_book = get_object_or_404(Audiobook.objects, _id=_id)
            audio_book.delete()

            return JsonResponse({"result": "success", "message": "Audiobook is deleted successfully."},
                                status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Audiobook record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting Audiobook: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting Audiobook"},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class ItemCategoryView(APIView):
    """
    E-commerce item category class based view
    """
    @extend_schema(
        tags=["Item Category"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            item_categories = ItemCategory.objects.all().order_by("-record_time")

            if not item_categories:
                raise Http404

            paginator = ItemCategoryDataPagination()
            item_categories_list = paginator.paginate_category(request, item_categories)

            return JsonResponse(
                {"result": "success", "message": "Item categories list", "content": item_categories_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Item categories are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching item categories: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching item categories."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Item Category"],
        request=AddItemCategorySerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddItemCategorySerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            name = serializer.validated_data["name"]
            description = serializer.validated_data["description"]
            measurement = serializer.validated_data["category-measurement"]
            color = serializer.validated_data["color"]
            icon = serializer.validated_data["icon"]

            # Value Validation
            validator = ItemCategoryValidator(serializer.validated_data,
                                                   fields=["name", "description", "measurement", "color", "icon"],
                                                   null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                if ItemCategory.objects.filter(name=name.lower()).exists():
                    raise TitleDuplicationException("Item category name is already used.")

                # Upload icon
                file_name = str(uuid.uuid4())
                if icon is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "item/category",
                                             file_name + '.' + icon.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in icon.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + icon.name.split('.')[-1]

                item_category = ItemCategory.objects.create(
                    name=name.lower(),
                    description=description,
                    color=color,
                    measurement=measurement,
                    icon=file_name,
                    created_at=today,
                    updated_at=today
                )
                item_category.save()

                return JsonResponse({"result": "success", "message": "Item category is added successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating item category: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating item category"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Item Category"],
        request=UpdateItemCategorySerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdateItemCategorySerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            name = serializer.validated_data["name"]
            description = serializer.validated_data["description"]
            measurement = serializer.validated_data["edit-category-measurement"]
            color = serializer.validated_data["color"]
            icon = serializer.validated_data["icon"]

            if not _id:
                raise UUIDException("Record is not found.")

            # Value Validation
            validator = ItemCategoryValidator(serializer.validated_data,
                                                   fields=["name", "description", "measurement", "color", "icon"])

            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                item_category = ItemCategory.objects.select_for_update().filter(_id=_id).first()
                if not item_category:
                    raise Http404("Item category is not found.")

                if ItemCategory.objects.filter(Q(name=name.lower()) & ~Q(_id=_id)).exists():
                    raise TitleDuplicationException("Item category name is already used.")

                # Upload icon
                file_name = str(uuid.uuid4())
                if icon is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "item/category",
                                             file_name + '.' + icon.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in icon.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + icon.name.split('.')[-1]
                    item_category.icon = file_name

                if name:
                    item_category.name = name.lower()
                if description:
                    item_category.description = description
                if measurement:
                    item_category.measurement = measurement
                if color:
                    item_category.color = color
                item_category.save()

                return JsonResponse({"result": "success", "message": "Item category is updated successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Item category is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating item category: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating item category"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            item_category = get_object_or_404(ItemCategory.objects, _id=_id)
            item_category.delete()

            return JsonResponse({"result": "success", "message": "Item category is deleted successfully."},
                                status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Item category record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting item category: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting item category"},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class ItemView(APIView):
    """
    E-commerce item class based view
    """
    @extend_schema(
        tags=["Item"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            items = Item.objects.all().order_by("-record_time")

            if not items:
                raise Http404

            paginator = ItemDataPagination()
            items_list = paginator.paginate_item(request, items)

            return JsonResponse(
                {"result": "success", "message": "Items list", "content": items_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Items are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching items: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching items."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Item Category"],
        request=AddItemSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddItemSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            name = serializer.validated_data["name"]
            overview = serializer.validated_data["overview"]
            description = serializer.validated_data["description"]
            thumbnail = serializer.validated_data["thumbnail"]
            category = serializer.validated_data["category"]
            min_value = serializer.validated_data["min-value"]
            max_value = serializer.validated_data["max-value"]
            sizes = serializer.validated_data["size-selection"]
            price = serializer.validated_data["price"]
            variation_img = serializer.validated_data["variation_img"]
            variation_color = serializer.validated_data["variation_color"]
            variation_qty = serializer.validated_data["variation_qty"]

            # Value Validation
            validator = ItemValidator(serializer.validated_data,
                                              fields=["name", "overview", "description", "thumbnail", "category", "min-value", "max-value",
                                                      "size-selection", "price", "variation_img", "variation_color", "variation_qty"],
                                                    null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                if Item.objects.filter(name=name.lower()).exists():
                    raise TitleDuplicationException("Item name is already used.")

                item_category = ItemCategory.objects.select_for_update().filter(_id=category).first()
                if not item_category:
                    raise Http404("Item category is not found.")

                # Upload thumbnail
                file_name = str(uuid.uuid4())
                if thumbnail is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "item/item-thumbnail",
                                             file_name + '.' + thumbnail.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in thumbnail.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + thumbnail.name.split('.')[-1]

                # handle the variations
                variation_img_file_names = []
                variation_color_codes = []
                variation_qty_count = []
                if variation_img is not None or len(variation_img) > 0:
                    for img in variation_img:
                        file_name = str(uuid.uuid4())
                        file_path = os.path.join(settings.MEDIA_ROOT, "item/ecommerce-variation",
                                                 file_name + '.' + img.name.split('.')[-1])
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'wb+') as destination:
                            for chunk in img.chunks():
                                destination.write(chunk)
                        file_name = file_name + '.' + img.name.split('.')[-1]
                        variation_img_file_names.append(file_name)
                        # append respective color values
                        index = variation_img.index(img)
                        variation_color_codes.append(variation_color[index])
                        # append corresponding quality values
                        variation_qty_count.append(variation_qty[index])

                # calculate total quantity
                total_quantity = 0
                total_quantity += sum(map(int, variation_qty_count))

                item = Item.objects.create(
                    name=name.lower(),
                    category=category,
                    min_value=min_value,
                    max_value=max_value,
                    sizes=sizes,
                    thumbnail=file_name,
                    overview=overview,
                    description=description,
                    variation_img=variation_img,
                    variation_color=variation_color,
                    variation_qty=variation_qty,
                    price=price,
                    quantity=total_quantity,
                    created_at=today,
                    updated_at=today
                )
                item.save()

                # Update item category
                item_category.item_count = F("item_count") + 1
                item_category.save(update_fields=["item_count"])
                item_category.refresh_from_db(fields=["item_count"])

                return JsonResponse({"result": "success", "message": "Item is added successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating item: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating item"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Item"],
        request=UpdateItemSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdateItemSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            name = serializer.validated_data["name"]
            overview = serializer.validated_data["overview"]
            description = serializer.validated_data["description"]
            thumbnail = serializer.validated_data["thumbnail"]
            category = serializer.validated_data["category"]
            min_value = serializer.validated_data["min-value"]
            max_value = serializer.validated_data["max-value"]
            sizes = serializer.validated_data["size-selection"]
            price = serializer.validated_data["price"]
            variation_img = serializer.validated_data["variation_img"]
            variation_color = serializer.validated_data["variation_color"]
            variation_qty = serializer.validated_data["variation_qty"]

            if not _id:
                raise UUIDException("Record is not found.")

            # Value Validation
            validator = ItemValidator(serializer.validated_data,
                                      fields=["name", "overview", "description", "thumbnail", "category", "min-value",
                                              "max-value", "size-selection", "price", "variation_img", "variation_color",
                                              "variation_qty"])

            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                item = Item.objects.select_for_update().filter(_id=_id).first()
                if not item:
                    raise Http404("Item is not found.")

                if Item.objects.filter(Q(name=name.lower()) & ~Q(_id=_id)).exists():
                    raise TitleDuplicationException("Item name is already used.")

                # Upload thumbnail
                file_name = str(uuid.uuid4())
                if thumbnail is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "item/item-thumbnail",
                                             file_name + '.' + thumbnail.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in thumbnail.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + thumbnail.name.split('.')[-1]
                    item.thumbnail = file_name

                # handle the variations
                variation_img_file_names = []
                variation_color_codes = []
                variation_qty_count = []
                if variation_img is not None or len(variation_img) > 0:
                    for img in variation_img:
                        file_name = str(uuid.uuid4())
                        file_path = os.path.join(settings.MEDIA_ROOT, "item/ecommerce-variation",
                                                 file_name + '.' + img.name.split('.')[-1])
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'wb+') as destination:
                            for chunk in img.chunks():
                                destination.write(chunk)
                        file_name = file_name + '.' + img.name.split('.')[-1]
                        variation_img_file_names.append(file_name)
                        # append respective color values
                        index = variation_img.index(img)
                        variation_color_codes.append(variation_color[index])
                        # append corresponding quality values
                        variation_qty_count.append(variation_qty[index])
                item.variation_img = variation_img_file_names
                item.variation_color = variation_color_codes
                item.variation_qty = variation_qty_count

                total_quantity = 0
                total_quantity += sum(map(int, variation_qty_count))
                item.quantity = total_quantity

                pre_category = get_object_or_404(ItemCategory.objects, _id=item.category)
                if category:
                    new_category = get_object_or_404(ItemCategory.objects, _id=category)

                    pre_category.assigned_audio = F("item_count") - 1
                    pre_category.save(update_fields=["item_count"])

                    new_category.assigned_audio = F("item_count") + 1
                    new_category.save(update_fields=["item_count"])

                    item.category = category

                if name != '':
                    item.name = name.lower()
                if overview != '':
                    item.overview = overview
                if description != '':
                    item.description = description
                if min_value:
                    item.min_value = min_value
                if max_value:
                    item.max_value = max_value
                if sizes and len(sizes) != 0:
                    item.sizes = sizes
                if price:
                    item.price = price
                item.save()

                return JsonResponse({"result": "success", "message": "Item is updated successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Item is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating item: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating item"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Item"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            item = get_object_or_404(Item.objects, _id=_id)
            item.delete()

            return JsonResponse({"result": "success", "message": "Item is deleted successfully."},
                                status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Item record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting item: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting item"},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class ItemCartView(APIView):
    """
    Cart class based view
    """

    @extend_schema(
        tags=["Cart Fetch"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            carts = Cart.objects.all().order_by("-record_time")

            if not carts:
                raise Http404

            paginator = ItemCartDataPagination()
            carts_list = paginator.paginate_cart(request, carts)

            return JsonResponse(
                {"result": "success", "message": "Users's cart list", "content": carts_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Carts are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching carts: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching carts."},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class ItemWishlistView(APIView):
    """
    Wishlist class based view
    """

    @extend_schema(
        tags=["Wishlist Fetch"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            wishlists = Wishlist.objects.all().order_by("-record_time")

            if not wishlists:
                raise Http404

            paginator = ItemWishlistDataPagination()
            wishlists_list = paginator.paginate_wishlist(request, wishlists)

            return JsonResponse(
                {"result": "success", "message": "Users's wishlist list", "content": wishlists_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Wishlist are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching wishlist: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching wishlist."},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class PaymentMethodView(APIView):
    """
    Package Plan class based view
    """

    @extend_schema(
        tags=["Payment Method"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            methods = PaymentMethod.objects.all().order_by("-record_time")

            if not methods:
                raise Http404

            paginator = PaymentMethodDataPagination()
            methods_list = paginator.paginate_payment_method(request, methods)

            return JsonResponse(
                {"result": "success", "message": "Payment methods list", "content": methods_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Payment methods are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching payment methods: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching payment methods."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Payment Method"],
        request=AddPaymentMethodSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddPaymentMethodSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            name = serializer.validated_data["name"]
            icon = serializer.validated_data["icon"]
            holder = serializer.validated_data["holder"]
            num = serializer.validated_data["num"]

            # Value Validation
            validator = PaymentMethodValidator(serializer.validated_data,
                                              fields=["name", "icon", "holder", "num"],
                                              null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                if PaymentMethod.objects.filter(name=name.lower()).exists():
                    raise TitleDuplicationException("Payment method name is already used.")
                if PaymentMethod.objects.filter(account_num=num).exists():
                    raise ValueDuplicationException("Payment method's account number is already used.")
                # Upload icon
                file_name = str(uuid.uuid4())
                if icon is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "payment-method/icon",
                                             file_name + '.' + icon.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in icon.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + icon.name.split('.')[-1]

                payment_method = PaymentMethod.objects.create(
                    name=name.lower(),
                    account_holder=holder,
                    account_num=num,
                    icon=file_name,
                    created_at=today,
                    updated_at=today
                )
                payment_method.save()

                return JsonResponse({"result": "success", "message": "Payment method is added successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, TitleDuplicationException, ValueDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating payment method: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating payment method"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Payment Method"],
        request=UpdatePaymentMethodSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdatePaymentMethodSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            name = serializer.validated_data["name"]
            icon = serializer.validated_data["icon"]
            holder = serializer.validated_data["holder"]
            num = serializer.validated_data["num"]

            if not _id:
                raise UUIDException("Record is not found.")

            # Value Validation
            validator = PaymentMethodValidator(serializer.validated_data,
                                      fields=["name", "icon", "holder", "num"])

            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                payment_method = PaymentMethod.objects.select_for_update().filter(_id=_id).first()
                if not payment_method:
                    raise Http404("Payment method is not found.")

                if PaymentMethod.objects.filter(Q(name=name.lower()) & ~Q(_id=_id)).exists():
                    raise TitleDuplicationException("Payment method name is already used.")

                if PaymentMethod.objects.filter(Q(account_num=num) & ~Q(_id=_id)).exists():
                    raise ValueDuplicationException("Payment method account number is already used.")

                # Upload icon
                file_name = str(uuid.uuid4())
                if icon is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "payment-method/icon",
                                             file_name + '.' + icon.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in icon.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + icon.name.split('.')[-1]
                    payment_method.icon = file_name

                if name != '':
                    payment_method.name = name.lower()
                if holder != '':
                    payment_method.account_holder = holder
                if num != '':
                    payment_method.account_num = num

                payment_method.save()

                return JsonResponse({"result": "success", "message": "Payment method is updated successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException, ValidationException, TitleDuplicationException, ValueDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Payment method is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating payment method: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating payment method"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Payment Method"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            payment_method = get_object_or_404(PaymentMethod.objects, _id=_id)
            payment_method.delete()

            return JsonResponse({"result": "success", "message": "Payment method is deleted successfully."},
                                status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Payment method record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting payment method: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting payment method"},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class PackagePlanView(APIView):
    """
    Package plan class based view
    """

    @extend_schema(
        tags=["Package Plan"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            packages = Package.objects.all().order_by("-record_time")

            if not packages:
                raise Http404

            paginator = PackagePlanDataPagination()
            packages_list = paginator.paginate_package(request, packages)

            return JsonResponse(
                {"result": "success", "message": "Package plans list", "content": packages_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Package plans are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching package plans: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching package plans."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Package Plan"],
        request=AddPackagePlanSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddPackagePlanSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            name = serializer.validated_data["name"]
            overview = serializer.validated_data["overview"]
            price = serializer.validated_data["price"]
            entities = serializer.validated_data["entities"]
            offers = serializer.validated_data["offers"]


            # Value Validation
            validator = PackagePlanValidator(serializer.validated_data,
                                               fields=["name", "overview", "price", "entities", "offers"],
                                               null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                if Package.objects.filter(name=name.lower()).exists():
                    raise TitleDuplicationException("Package plan name is already used.")

                package = Package.objects.create(
                    name=name.lower(),
                    overview=overview,
                    price=price,
                    entity=entities,
                    offers=offers,
                    created_at=today,
                    updated_at=today
                )
                package.save()

                return JsonResponse({"result": "success", "message": "Package plan is added successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating package plan: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating package plan"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Package Plan"],
        request=UpdatePackagePlanSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdatePackagePlanSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            name = serializer.validated_data["name"]
            overview = serializer.validated_data["overview"]
            price = serializer.validated_data["price"]
            entities = serializer.validated_data["entities"]
            offers = serializer.validated_data["offers"]

            if not _id:
                raise UUIDException("Record is not found.")

            # Value Validation
            validator = PackagePlanValidator(serializer.validated_data,
                                               fields=["name", "overview", "price", "entities", "offers"])

            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                package_plan = Package.objects.select_for_update().filter(_id=_id).first()
                if not package_plan:
                    raise Http404("Package plan is not found.")

                if Package.objects.filter(Q(name=name.lower()) & ~Q(_id=_id)).exists():
                    raise TitleDuplicationException("Package plan name is already used.")

                if name != '':
                    package_plan.name = name.lower()
                if overview != '':
                    package_plan.overview = overview
                if price != '':
                    package_plan.price = price
                if entities != '':
                    package_plan.entities = entities
                if offers != '':
                    package_plan.offers = offers

                package_plan.save()

                return JsonResponse({"result": "success", "message": "Package plan is updated successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException, ValidationException, TitleDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Package plan is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating package plan: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating package plan"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Package Plan"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            package_plan = get_object_or_404(Package.objects, _id=_id)
            package_plan.delete()

            return JsonResponse({"result": "success", "message": "Package plan is deleted successfully."},
                                status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Payment plan record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting package plan: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting package plan"},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class EcommercePCView(APIView):
    """
    E-commerce payment confirmation view
    """

    @extend_schema(
        tags=["Ecommerce PC"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            ecommerce_pcs = EcommercePC.objects.all().order_by("-record_time")

            if not ecommerce_pcs:
                raise Http404

            paginator = EcommercePCDataPagination()
            ecommerce_pcs_list = paginator.paginate_pc(request, ecommerce_pcs)

            return JsonResponse(
                {"result": "success", "message": "Ecommerce PC list", "content": ecommerce_pcs_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Ecommerce PC are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching ecommerce pcs: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching ecommerce pcs."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Ecommerce PC"],
        request=AddEcommercePCSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddEcommercePCSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            order_id = serializer.validated_data["order_id"]
            user_name = serializer.validated_data["user_name"]
            user_email = serializer.validated_data["user_email"]
            user_phone = serializer.validated_data["user_phone"]
            items = serializer.validated_data["items"]
            price = serializer.validated_data["price"]
            method_id = serializer.validated_data["method"]
            proof = serializer.validated_data["proof"]

            # Value Validation
            validator = EcommercePCValidator(serializer.validated_data,
                                             fields=["order_id", "user_name", "user_email", "user_phone", "items", "price", "method_id",
                                                     "proof"],
                                             null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                if EcommercePC.objects.filter(order_id=order_id).exists():
                    raise DuplicationException("Order ID is already found.")

                if not PaymentMethod.objects.filter(_id=method_id).exists():
                    raise ValueErrorException("Payment method is not found.")

                # Upload payment proof
                file_name = str(uuid.uuid4())
                if proof is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "PC/ecommerce",
                                             file_name + '.' + proof.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in proof.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + proof.name.split('.')[-1]

                ecommerce_pc = EcommercePC.objects.create(
                    order_id=order_id,
                    user_name=user_name,
                    user_email=user_email,
                    user_phone=user_phone,
                    items=items,
                    total_price=price,
                    method_id=method_id,
                    proof=file_name,
                    created_at=today,
                    updated_at=today
                )
                ecommerce_pc.save()

                return JsonResponse({"result": "success", "message": "Ecommerce payment confirmation is added successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, TitleDuplicationException, DuplicationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating ecommerce pc: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating ecommerce pc"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Ecommerce PC"],
        request=UpdateEcommercePCSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdateEcommercePCSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            _status = serializer.validated_data["status"]

            if not _id:
                raise UUIDException("Record is not found.")

            with transaction.atomic():
                ecommerce_pc = EcommercePC.objects.select_for_update().filter(_id=_id).first()
                if not ecommerce_pc:
                    raise Http404("Payment confirmation is not found.")

                if _status:
                    ecommerce_pc.status = _status

                ecommerce_pc.save()

                return JsonResponse({"result": "success", "message": "Ecommerce PC is updated successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Ecommerce PC is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating ecommerce pc: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating ecommerce pc"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Ecommerce PC"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            ecommerce_pc = get_object_or_404(EcommercePC.objects, _id=_id)
            ecommerce_pc.delete()

            return JsonResponse({"result": "success", "message": "Ecommerce PC is deleted successfully."},
                                status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Ecommerce PC record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting ecommerce pc: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting ecommerce pc"},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class PackagePCView(APIView):
    """
    Package payment confirmation class based view
    """

    @extend_schema(
        tags=["Package PC"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            package_pcs = PackagePC.objects.all().order_by("-record_time")

            if not package_pcs:
                raise Http404

            paginator = PackagePCDataPagination()
            package_pcs_list = paginator.paginate_pc(request, package_pcs)

            return JsonResponse(
                {"result": "success", "message": "Package PC list", "content": package_pcs_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Package PC are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching package pcs: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching package pcs."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Package PC"],
        request=AddPackagePCSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddPackagePCSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            package = serializer.validated_data["package"]
            email = serializer.validated_data["email"]
            method_id = serializer.validated_data["method"]
            proof = serializer.validated_data["proof"]

            # Value Validation
            validator = PackagePCValidator(serializer.validated_data,
                                             fields=["package", "email", "method_id", "proof"],
                                             null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                if not PaymentMethod.objects.filter(_id=method_id).exists():
                    raise ValueErrorException("Payment method is not found.")

                if not Package.objects.filter(_id=package).exists():
                    raise ValueErrorException("Selected package is not found")
                price = Package.objects.get(_id=package).price

                # Upload payment proof
                file_name = str(uuid.uuid4())
                if proof is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "PC/package",
                                             file_name + '.' + proof.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in proof.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + proof.name.split('.')[-1]
                package_pc = PackagePC.objects.create(
                    package_id=package,
                    user_id=email,
                    price=price,
                    proof=file_name,
                    method_id=method_id,
                    created_at=today,
                    updated_at=today
                )
                package_pc.save()

                return JsonResponse(
                    {"result": "success", "message": "Package payment confirmation is added successfully."},
                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating package pc: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating package pc"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Package PC"],
        request=UpdatePackagePCSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdatePackagePCSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            _status = serializer.validated_data["status"]

            if not _id:
                raise UUIDException("Record is not found.")

            with transaction.atomic():
                package_pc = PackagePC.objects.select_for_update().filter(_id=_id).first()
                if not package_pc:
                    raise Http404("Payment confirmation is not found.")

                if _status:
                    package_pc.status = _status

                package_pc.save()

                return JsonResponse({"result": "success", "message": "Package PC is updated successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Package PC is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating package pc: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating package pc"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Package PC"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            package_pc = get_object_or_404(PackagePC.objects, _id=_id)
            package_pc.delete()

            return JsonResponse({"result": "success", "message": "Package PC is deleted successfully."},
                                status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Package PC record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting package pc: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting package pc"},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class AppointmentView(APIView):
    """
    Appointment class based view
    """

    @extend_schema(
        tags=["Appointment"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            appointments = Appointment.objects.all().order_by("-record_time")

            if not appointments:
                raise Http404

            paginator = AppointmentDataPagination()
            appointments_list = paginator.paginate_appointment(request, appointments)

            return JsonResponse(
                {"result": "success", "message": "Package PC list", "content": appointments_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Appointment are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching appointment: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching appointment."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Appointment"],
        request=AddAppointmentSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddAppointmentSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            customer = serializer.validated_data["customer"]
            subject = serializer.validated_data["subject"]
            message = serializer.validated_data["message"]
            schedule = serializer.validated_data["schedule"]

            # Value Validation
            validator = AppointmentValidator(serializer.validated_data,
                                           fields=["customer", "subject", "message", "schedule"],
                                           null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Check whether customer exists or not
                appointment = Appointment.objects.create(
                    customer=customer,
                    subject=subject,
                    message=message,
                    schedule=schedule,
                    created_at=today,
                    updated_at=today
                )
                appointment.save()

                return JsonResponse(
                    {"result": "success", "message": "Appointment is added successfully."},
                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating appointment: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating appointment"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Appointment"],
        request=UpdateAppointmentSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdateAppointmentSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data["_id"]
            link = serializer.validated_data["link"]
            _status = serializer.validated_data["status"]

            if not _id:
                raise UUIDException("Record is not found.")

            with transaction.atomic():
                appointment = Appointment.objects.select_for_update().filter(_id=_id).first()
                if not appointment:
                    raise Http404

                if link:
                    appointment.link = link
                if _status:
                    appointment.status = _status

                appointment.save()

                return JsonResponse({"result": "success", "message": "Appointment is updated successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Appointment is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating appointment: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating appointment"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Appointment"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            appointment = get_object_or_404(Appointment.objects, _id=_id)
            appointment.delete()

            return JsonResponse({"result": "success", "message": "Appointment is deleted successfully."},
                                status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Appointment record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting appointment: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting appointment"},
                                status=status.HTTP_400_BAD_REQUEST)

@permission_classes([IsAuthenticated, role_required(["super_admin", "admin"])])
class LocalizationView(APIView):
    """
    Localization class based view
    """

    @extend_schema(
        tags=["Localization"],
        responses={200: dict}
    )
    def get(self, request):
        try:
            localization = Localization.objects.all().order_by("-record_time")

            if not localization:
                raise Http404

            paginator = LocalizationDataPagination()
            localizations_list = paginator.paginate_localization(request, localization)

            return JsonResponse(
                {"result": "success", "message": "Localizations list", "content": localizations_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Localizations are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching localizations: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching localizations."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Localization"],
        request=AddLocalizationSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = AddLocalizationSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            content_key = serializer.validated_data["content_key"]
            content_value = serializer.validated_data["content_value"]
            entity = serializer.validated_data["entity"]

            with transaction.atomic():
                formats = Localization.objects.all()

                if formats.filter(Q(content_key=content_key) & Q(entity=entity)).first():
                    return JsonResponse({"result": "error", "message": "Content key is already found"},
                                        status=200)

                localization = Localization.objects.create(
                    content_key=content_key,
                    content_value=content_value,
                    entity=entity,
                    created_at=today,
                    updated_at=today
                )
                localization.save()

                return JsonResponse(
                    {"result": "success", "message": "Localization is added successfully."},
                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating localization: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating localization"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Localization"],
        request=UpdateLocalizationSerializer,
        responses={200: dict}
    )
    def patch(self, request):
        serializer = UpdateLocalizationSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            format_id = serializer.validated_data["format_id"]
            content_key = serializer.validated_data["content_key"]
            content_value = serializer.validated_data["content_value"]
            entity = serializer.validated_data["entity"]

            if not format_id:
                raise UUIDException("Record is not found.")

            with transaction.atomic():
                localization = Localization.objects.select_for_update().filter(_id=format_id).first()
                if not localization:
                    raise Http404

                if content_key:
                    localization.content_key = content_key
                if content_value:
                    localization.content_value = content_value
                if entity:
                    localization.entity = entity

                localization.save()

                return JsonResponse({"result": "success", "message": "Localization is updated successfully."},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, UUIDException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Localization is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating localization: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating localization"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Localization"],
        parameters=[OpenApiParameter(name="_id", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: dict}
    )
    def delete(self, request):
        _id = request.data.get("_id")
        try:
            if not _id:
                raise UUIDException("Record is not found.")

            localization = get_object_or_404(Localization.objects, _id=_id)
            localization.delete()

            return JsonResponse({"result": "success", "message": "Localization is deleted successfully."},
                                status=status.HTTP_200_OK)

        except UUIDException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Localization record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting localization: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting localization"},
                                status=status.HTTP_400_BAD_REQUEST)
