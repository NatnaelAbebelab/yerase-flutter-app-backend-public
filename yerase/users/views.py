import logging
import os
import random
import secrets
import string
from datetime import date

from django.db.models.fields import FloatField
from rest_framework import viewsets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models.functions import Cast
from django.db.models import Q, Sum
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .serializers import *
from .utility.token import get_tokens_for_user
from rest_framework.decorators import permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from string import capwords

from utils.exceptions import *
from utils.permissions import role_required
from .models import CustomUsers, Playlist
from .requestSerializers import *
from .services.validations import *
from .services.pagination import *
from .services.roles import get_user_role

# Create your views here.
logger = logging.getLogger(__name__)
today = date.today()
User = get_user_model()

"""
These are class based view to execute operation
"""
def generate_temp_password(length=8):
    if length < 8:
        raise ValueError("Password length must be at least 8")

    # At least one from each required category
    uppercase = secrets.choice(string.ascii_uppercase)
    lowercase = secrets.choice(string.ascii_lowercase)
    digit = secrets.choice(string.digits)
    # Other characters can be from letters, digits, punctuation
    others_length = length - 3
    others = ''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(others_length))

    # Combine all parts
    password_list = list(uppercase + lowercase + digit + others)

    # Shuffle to avoid predictable placement
    secrets.SystemRandom().shuffle(password_list)

    return ''.join(password_list)
def generate_otp():
    return str(random.randint(10000, 99999))

#===================> View Sets <=============================

class CustomerAccountViewSet(viewsets.ViewSet):
    """
    Register ViewSet to handle user registration
    """
    @extend_schema(
        tags=["Customer Accounts"],
        request=CreateAccountSerializer,
        responses={200: dict},
        #summary = "User registration",
        description = "Users create account"
    )

    @action(detail=False, methods=['post'], url_path='create')
    def create_account(self, request):
        serializer = CreateAccountSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            fname = serializer.validated_data["fname"]
            lname = serializer.validated_data["lname"]
            email = serializer.validated_data["email"]
            phone = serializer.validated_data["phone"]
            password = serializer.validated_data["password"]
            weight = serializer.validated_data["weight"]
            height = serializer.validated_data["height"]
            age = serializer.validated_data["age"]
            gender = serializer.validated_data["gender"] # Value M or F

            # Value Validation
            validator = UserAccountDataValidator(serializer.validated_data,
                                             fields=["fname", "lname", "email", "phone", "password",
                                                     "weight", "height", "age", "gender"],
                                             null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Check email and phone must be unique
                customers = CustomUsers.objects.all()
                if CustomUser.objects.filter(username=email.lower()).exists():
                    raise ValueDuplicationException("Email address is already used.")
                if customers.filter(phone=phone).exists():
                    raise ValueDuplicationException("Phone number is already used.")

                while True:
                    otp_code = generate_otp()
                    if customers.filter(otp_code=otp_code).count() > 0:
                        continue
                    else:
                        break

                user = CustomUser.objects.create(
                    first_name=fname,
                    last_name=lname,
                    username=email.lower(),
                    email=email.lower(),
                    password=make_password(password),
                )
                user.save()

                customer = CustomUsers.objects.create(
                    user=user,
                    phone=phone.lower(),
                    weight=weight,
                    height=height,
                    age=age,
                    gender=gender,
                    otp_code=otp_code,
                    created_at=today,
                    updated_at=today,
                )
                customer.save()

                serializer = CustomerUsersAccountSerializer(customer).data

                # send email notification / OTP
                context = {
                    'fname': fname.capitalize(),
                    'lname': lname.capitalize(),
                    'email': email,
                    'otp_code': otp_code
                }
                template = get_template('add-customer-email-template.html')
                message_content = template.render(context)
                subject = 'Activate Your Account'
                message = message_content
                email = EmailMessage(subject, message, 'natnaelabebelab@gmail.com', [email])
                email.content_subtype = 'html'
                email.send()

                return Response(
                    {"result": "success", "message": "You have signed up successfully. Activate your account to sign in.", "content": serializer},
                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueDuplicationException) as e:
            return Response({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return Response({"result": "error", "message": "Record is not found."},
                           status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating customer: %s", e)
            return Response({"result": "error", "message": "Error occurred while creating customer"},
                           status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Customer Accounts"],
        request=AccountActivationSerializer,
        responses={200: dict},
        description="Activate user account"
    )
    @action(detail=False, methods=['post'], url_path='activate')
    def activate_user_account(self, request):
        serializer = AccountActivationSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            otp_code = serializer.validated_data["otp_code"]
            email = serializer.validated_data.get("email").lower()


            # Value Validation
            validator = AccountActivationDataValidator(serializer.validated_data,
                                                       fields=["otp_code", "email"],
                                                       null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                if not CustomUsers.objects.filter(otp_code=otp_code).exists():
                    raise ValueErrorException("OTP code is not found")

                user = get_object_or_404(CustomUser.objects, email=email)
                customer = get_object_or_404(CustomUsers.objects, user=user)

                customer.otp_code = '1'
                customer.save()
                if user.email == email and user.username == email:
                    login(request, user)
                    return JsonResponse(
                        {"result": "success", "message": "You have activates your account successfully."},
                        status=status.HTTP_200_OK)
                return JsonResponse({"result": "error", "message": "Your account is not found"},
                                    status=status.HTTP_404_NOT_FOUND)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while activating account: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while activating account"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Customer Accounts"],
        responses={200: dict},
        description="Resend Activation Code"
    )
    @action(detail=False, methods=['post'], url_path='resend-otp-code')
    def resend_otp_code(self, request):
        try:
            email = request.query_params.get("email")

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=email)
                customer = get_object_or_404(CustomUsers.objects, user=user)

                if customer.otp_code == '1':
                    return JsonResponse({
                        "result": "success",
                        "message": "Your account is already active.",
                        "content": {}
                    })

                # generate new opt code
                while True:
                    otp_code = generate_otp()
                    if CustomUsers.objects.filter(otp_code=otp_code).count() > 0:
                        continue
                    else:
                        break
                customer.otp_code = otp_code
                customer.save()

                serializer = CustomerUsersAccountSerializer(customer).data

                # send email notification / OTP
                context = {
                    'fname': user.first_name.capitalize(),
                    'lname': user.last_name.capitalize(),
                    'email': user.email,
                    'otp_code': otp_code
                }
                template = get_template('add-customer-email-template.html')
                message_content = template.render(context)
                subject = 'Activate Your Account'
                message = message_content
                email = EmailMessage(subject, message, 'natnaelabebelab@gmail.com', [email])
                email.content_subtype = 'html'
                email.send()

                return JsonResponse(
                    {"result": "success", "message": "New activation code is sent your e-mail inbox.", "content": serializer},
                    status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while resending opt code: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while sending otp code"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Customer Accounts"],
        request=SignInSerializer,
        responses={200: dict},
        description="Sign in to user account"
    )
    @action(detail=False, methods=['post'], url_path='sign-in')
    def sign_in(self, request):
        serializer = SignInSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            email = serializer.validated_data.get("email").lower()
            password = serializer.validated_data.get("password")

            # Value Validation
            validator = UserAccountDataValidator(serializer.validated_data,
                                                 fields=["email", "password"],
                                                 null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                if not CustomUser.objects.filter(email=email.lower()).exists():
                    raise ValueErrorException("Email address is not found")

                user = get_object_or_404(CustomUser.objects, email=email)
                customer = get_object_or_404(CustomUsers, user=user)

                if customer.otp_code != '1':
                    while True:
                        otp_code = generate_otp()
                        if CustomUsers.objects.filter(otp_code=otp_code).exists():
                            continue
                        else:
                            break

                    customer.otp_code = otp_code
                    customer.save()

                    # send email notification / OTP
                    context = {
                        'fname': user.first_name.capitalize(),
                        'lname': user.last_name.capitalize(),
                        'email': user.email,
                        'otp_code': otp_code
                    }
                    template = get_template('add-customer-email-template.html')
                    message_content = template.render(context)
                    subject = 'Activate Your Account'
                    message = message_content
                    email = EmailMessage(subject, message, 'natnaelabebelab@gmail.com', [email])
                    email.content_subtype = 'html'
                    email.send()

                    return JsonResponse(
                        {
                            "result": "error",
                            "message": "Your account is not activated. We sent activation code to your email."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if check_password(password, user.password):
                    login(request, user)
                    tokens = get_tokens_for_user(user)
                    role = get_user_role(request.user)
                    return JsonResponse({"result": "success", "message": "You have signed in successfully", "content": {"logged_user": user.username, "tokens": tokens}},
                                        status=status.HTTP_200_OK)

                return JsonResponse({"result": "error", "message": "Your account is not found"},
                                    status=status.HTTP_404_NOT_FOUND)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while signing in: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while signing in"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Customer Accounts"],
        request=ResetUserPasswordSerializer,
        responses={200: dict},
        description="Reset your password"
    )
    @action(detail=False, methods=['post'], url_path='reset-password')
    def reset_password(self, request):
        serializer = ResetUserPasswordSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            email = serializer.validated_data["email"]

            # Value Validation
            validator = UserAccountDataValidator(serializer.validated_data,
                                                 fields=["email"],
                                                 null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                if not CustomUser.objects.filter(email=email.lower()).exists():
                    raise ValueErrorException("Email address is not found")

                user = get_object_or_404(CustomUser.objects, email=email.lower())

                # generate password
                temp_password = generate_temp_password(8)

                user.password = make_password(temp_password)
                user.save()

                context = {
                    'fname': user.first_name.capitalize(),
                    'password': temp_password # open app reset screen from URL
                }
                template = get_template('customer-reset-password-template.html')
                message_content = template.render(context)
                subject = 'Reset Your Password'
                message = message_content
                email = EmailMessage(subject, message, 'natnaelabebelab@gmail.com', [email])
                email.content_subtype = 'html'  # Specify that the email content is HTML
                email.send()

                return JsonResponse({"result": "success", "message": "You've reset your password", "content": temp_password},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while resetting password: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while resetting password"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Customer Accounts"],
        request=UpdateAccountProfileSerializer,
        responses={200: dict},
        description="Update Account Setting"
    )
    @action(detail=False, methods=['patch'], url_path='update-account')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def update_account(self, request):
        serializer = UpdateAccountProfileSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            fname = serializer.validated_data.get("fname")
            lname = serializer.validated_data.get("lname")
            email = serializer.validated_data.get("email").lower()
            phone = serializer.validated_data.get("phone")
            weight = serializer.validated_data.get("weight")
            height = serializer.validated_data.get("height")
            age = serializer.validated_data.get("age")
            gender = serializer.validated_data.get("gender")
            profile = serializer.validated_data.get("profile")

            # Value Validation
            validator = UserAccountDataValidator(serializer.validated_data,
                                                 fields=["fname", "lname", "email", "phone", "weight", "height", "age",
                                                         "gender"], empty_validation=False, null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                if float(weight) < 20 or float(weight) < 0:
                    raise ValueErrorException("Weight must be above 20kg")
                if float(height) < 0:
                    raise ValueErrorException("Provide your actual height measurement")
                if int(age) < 0 or int(age) < 12:
                    raise ValueErrorException("You must be above 12 years old")

                if CustomUser.objects.filter(Q(email=email) & Q(username=email)).exists() and email != request.user:
                    raise ValueDuplicationException("Email is already in use")

                user = get_object_or_404(CustomUser.objects, email=request.user)
                customer = get_object_or_404(CustomUsers.objects, user=user)

                # Upload profile
                file_name = str(uuid.uuid4())
                if profile is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "users/profile",
                                             file_name + '.' + profile.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in profile.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + profile.name.split('.')[-1]

                if fname:
                    user.first_name = fname
                if lname:
                    user.last_name = lname
                if email:
                    user.email = email
                    user.username = email
                    request.user = email

                user.save()

                if phone:
                    customer.phone = phone
                if weight:
                    customer.weight = weight
                if height:
                    customer.height = height
                if age:
                    customer.age = age
                if gender:
                    customer.gender = gender
                if profile:
                    customer.profile = file_name

                customer.updated_at = timezone.now()
                customer.record_time = timezone.now()
                customer.save()

                serializer = CustomerUsersAccountSerializer(customer).data

                return JsonResponse({"result": "success", "message": "You've updated your profile", "content": serializer},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueErrorException, ValueDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating profile: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating profile"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: dict},
        description="Change your password"
    )
    @action(detail=False, methods=['patch'], url_path='change-password')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            current = serializer.validated_data.get("current")
            password = serializer.validated_data.get("password")

            # Value Validation
            validator = UserAccountDataValidator(serializer.validated_data,
                                                 fields=["password"], empty_validation=False, null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)
                if not check_password(current, user.password):
                    raise ValueErrorException("Your current password doesn't match")

                user.password = make_password(password)
                user.save()

                serializer = CustomerAccountSerializer(user).data
                return JsonResponse({"result": "success", "message": "You've updated your password", "content": serializer},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating password: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating password"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses={200: dict},
        description="Get Me"
    )
    @action(detail=False, methods=['get'], url_path='get-me')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def get_me(self, request):
        try:
            email = request.query_params.get("email")

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=email)
                customer = get_object_or_404(CustomUsers.objects, user=user)

                serializer = CustomerUsersAccountSerializer(customer).data

                return JsonResponse(
                    {"result": "success", "message": "Your profile data", "content": serializer},
                    status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while getting me: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while getting me"},
                                status=status.HTTP_400_BAD_REQUEST)

class AppointmentViewSet(viewsets.ViewSet):
    """
    Appointment view set to book virtual meeting
    """

    @extend_schema(
        tags=["Appointment User"],
        request=BookAppointmentSerializer,
        responses={200: dict},
        description="Appointment"
    )
    @action(detail=False, methods=['post'], url_path='request-schedule-appointment')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def request_schedule_appointment(self, request):
        serializer = BookAppointmentSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            subject = serializer.validated_data.get("subject")
            message = serializer.validated_data.get("message")
            schedule = serializer.validated_data.get("schedule")

            # Value Validation
            validator = AppointmentDataValidator(serializer.validated_data,
                                                 fields=["subject", "message", "schedule"])
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)

                today_date = date.today()
                schedule_date = datetime.strptime(schedule, "%Y-%m-%d").date() if isinstance(schedule, str) else schedule

                if schedule_date < today_date:
                    raise ValueErrorException("Reservation schedule must be in the coming days")

                appointment = Appointment.objects.create(
                    customer=user,
                    subject=subject,
                    message=message,
                    schedule=schedule,
                    created_at=today,
                    updated_at=today,
                )
                appointment.save()

                serializer = AppointmentSerializer(appointment).data

                return JsonResponse({"result": "success", "message": "You've requested appointment successfully", "content": serializer},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while requesting appointment: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while requesting appointment"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Appointment User"],
        responses={200: dict},
        description="Appointment"
    )
    @action(detail=False, methods=['get'], url_path='get-appointments')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def get_appointments(self, request):
        try:
            user = get_object_or_404(CustomUser.objects, username=request.user)
            appointments = Appointment.objects.filter(customer=user).all().order_by("-record_time")

            if not appointments:
                raise Http404

            paginator = AppointmentDataPagination()
            appointments_list = paginator.paginate_appointment(request, appointments)

            return JsonResponse(
                {"result": "success", "message": "User appointments list", "content": appointments_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "User appointment is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching user appointment: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching user appointment."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Appointment User"],
        responses={200: dict},
        description="Delete appointment by ID"
    )
    @action(detail=False, methods=['delete'], url_path='delete-appointment')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def delete_appointment(self, request):
        try:
            appointment_id = request.query_params.get("id")
            if not appointment_id:
                return JsonResponse({"result": "error", "message": "Appointment ID is required."},
                                    status=status.HTTP_400_BAD_REQUEST)

            user = get_object_or_404(CustomUser.objects, username=request.user)
            appointment = get_object_or_404(Appointment.objects, _id=appointment_id)

            if appointment.customer == user:
                appointment.delete()
            else:
                raise Http404

            return JsonResponse({"result": "success", "message": "Appointment deleted successfully."},
                                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Appointment not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting appointment: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting appointment."},
                                status=status.HTTP_400_BAD_REQUEST)

class EcommerceViewSet(viewsets.ViewSet):
    """
    Ecommerce view to access store
    """
    @extend_schema(
        tags=["E-commerce Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-items-categories')
    def get_items_categories(self, request):
        try:
            categories = ItemCategory.objects.all().order_by("-record_time")

            if not categories:
                raise Http404

            paginator = ItemCategoryDataPagination()
            categories_list = paginator.paginate_category(request, categories)

            return JsonResponse(
                {"result": "success", "message": "Item categories list", "content": categories_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Items categories is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching Items categories: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching Items categories."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["E-commerce Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-items')
    def get_items(self, request):
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
        tags=["E-commerce Users"],
        responses={200: dict},
        description="Get a specific item by ID"
    )
    @action(detail=False, methods=['get'], url_path='get-item')
    def get_item(self, request):
        try:
            _id = request.query_params.get("id")
            if not _id:
                return JsonResponse({"result": "error", "message": "Item ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            item = get_object_or_404(Item.objects, _id=_id)

            response = {
                "_id": item._id,
                "name": capwords(item.name),
                "category": {},
                "min_value": item.min_value,
                "max_value": item.max_value,
                "thumbnail": item.thumbnail,
                "overview": item.overview,
                "description": item.description,
                "variation": {},
                "measurement": {},
                "price": item.price,
                "total_purchase_count": item.total_purchase_count,
                "quantity": item.quantity,
                "review_counts": {},
                "reviews": {},
                "user_review": {}
            }

            category = ItemCategory.objects.filter(_id=item.category._id).first()
            category_name = capwords(category.name) if category else "UNCATEGORIZED"
            color = category.color

            response["category"] = {
                "name": category_name,
                "color": color
            }

            # Get variations
            variation = {}
            for index, v in enumerate(item.variation_qty):
                if int(v) > 0:
                    data = {
                        'img': item.variation_img[index],
                        'color': item.variation_color[index],
                        'index': index
                    }
                    variation[str(index)] = data

            response["variation"] = variation

            # Get measurements
            measurement = {
                'has_size': None,
                'has_quantity': 0, # False => it isn't stock avaiablity it is about range like 5-10 L or  5-10 kg
                'type': 'free',
                'min': 0,
                'max': 0
            }

            if category.measurement == 'l':
                measurement['has_quantity'] = 1
                measurement['type'] = 'Liter'  # Fixed typo
                measurement['min'] = item.min_value  # Ensure string
                measurement['max'] = item.max_value  # Ensure string
            elif category.measurement == 'kg':
                measurement['has_quantity'] = 1
                measurement['type'] = 'Mass'
                measurement['min'] = item.min_value  # Ensure string
                measurement['max'] = item.max_value  # Ensure string
            elif category.measurement == 's':
                measurement['has_quantity'] = 0
                measurement['has_size'] = 1
                measurement['type'] = 'Size'
            else:
                logger.error(f"Unknown measurement type '{category.measurement}' for category {category.name}")

            response["measurement"] = measurement

            # Get item review
            item_review = ItemReview.objects.filter(item=item).all()
            total_rate = item_review.aggregate(total_rate=Sum(Cast('rate', FloatField())))['total_rate']
            total_rate = total_rate if total_rate else 0
            review_count = item_review.count()
            average_review = round(float(total_rate / review_count if review_count != 0 else 4), 2)
            int_part, decimal_part = divmod(average_review, 1)
            my_array = ["Item"] * int(int_part)
            half_star = ["item"] * 1 if decimal_part != 0 else ["item"] * 0
            response["review_counts"]['average_review'] = average_review
            response["review_counts"]['fullstars'] = my_array
            response["review_counts"]['halfstars'] = half_star
            response["review_counts"]['total_review'] = item_review.count()

            # Get items review
            user = CustomUser.objects.filter(username=request.user).first() if request.user.is_authenticated else None
            if user:
                recent_reviews = item_review.filter(~Q(active_user=user))[:4]
            else:
                recent_reviews = item_review[:4]

            # Add recent reviews to response
            for r in recent_reviews:
                data = {
                    "review_id": r._id,
                    "photo": "user-11.jpg",  # Static photo for guest reviewers, you can customize here
                    "fullname": "Customer",
                    "div": "d-md-flex",
                    "display": "display-block",
                    "review": r.review,
                    "rate": ['item'] * int(float(r.rate))
                }
                response['reviews'][str(r._id)] = data

            # Get current user
            if user:
                current_user_review = item_review.filter(Q(active_user=user) & Q(status='publish')).first()
                if current_user_review:
                    u = get_object_or_404(CustomUsers.objects, user=user)
                    response["user_review"] = {
                        'photo': u.profile.url if hasattr(u.profile, 'url') else u.profile,
                        'fullname': string.capwords(user.first_name) + ' ' + string.capwords(user.last_name),
                        'review': current_user_review.review,
                        'rate': ['item'] * int(float(current_user_review.rate))
                    }

            return JsonResponse({"result": "success", "message": "Item found", "content": response}, status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse(
                {"result": "error", "message": "Item not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error("Error occurred while fetching item: %s", e)
            return JsonResponse(
                {"result": "error", "message": "Error occurred while fetching item."},
                status=status.HTTP_400_BAD_REQUEST
            )

    @extend_schema(
        tags=["E-commerce Users"],
        request=AddToCartSerializer,
        responses={200: dict},
        description="E-commerce view set"
    )
    @action(detail=False, methods=['post'], url_path='add-to-cart')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def add_to_cart(self, request):
        serializer = AddToCartSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            item = serializer.validated_data.get("item")
            quantity = serializer.validated_data.get("quantity")
            color = serializer.validated_data.get("color")
            measurement = serializer.validated_data.get("measurement") # It is a measurement unit

            # Value Validation
            validator = ToCartDataValidator(serializer.validated_data,
                                            fields=["item", "quantity", "color", "measurement"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)
                cart = Cart.objects.filter(owner=user).first()
                wishlist = Wishlist.objects.filter(owner=user).first()
                selected_item = get_object_or_404(Item.objects, _id=item)

                if cart:
                    price = selected_item.price
                    if not item in cart.items:
                        cart.items.append(item)
                        cart.quantity.append(quantity)
                        cart.color.append(color)
                        cart.measurement.append(measurement)
                        cart.total_price = float(cart.total_price) + (float(price) * int(quantity))

                    if item in cart.items:
                        index = cart.items.index(item)
                        if index < len(cart.quantity) and quantity != '':
                            cart.quantity[index] = int(cart.quantity[index]) + int(quantity)
                            cart.total_price = float(cart.total_price) + (float(price) * int(quantity))
                        if index < len(cart.color) and color != '':
                            cart.color[index] = color
                        if index < len(cart.measurement) and measurement != '':
                            cart.measurement[index] = measurement
                    # remove from wishlist
                    if wishlist:
                        if item in wishlist.items:
                            wishlist.total_price = float(wishlist.total_price) - float(price)
                            wishlist.items.pop(wishlist.items.index(item))
                            wishlist.updated_at = today
                            wishlist.record_time = today
                            wishlist.save()
                    cart.record_time = today
                    cart.save()

                    serializer = ItemCartSerializer(cart).data

                    return Response({"result": "success", "message": "Cart is updated successfully", "content": serializer},
                                    status=status.HTTP_200_OK)

                items_list = []
                quantity_list, color_list, measurement_list = [], [], []
                quantity_list.append(quantity)
                color_list.append(color)
                measurement_list.append(measurement)
                total_price = 0.00
                price = Item.objects.get(_id=item).price
                total_price = float(total_price) + (float(price) * int(quantity))
                items_list.append(item)

                cart = Cart.objects.create(
                    owner=user,
                    items=items_list,
                    quantity=quantity_list,
                    color=color_list,
                    measurement=measurement_list,
                    total_price=str(total_price),
                    created_at=today,
                    updated_at=today,
                    record_time=today
                )
                cart.save()

                serializer = ItemCartSerializer(cart).data
                # remove from wishlist
                if wishlist and item in wishlist.items:
                    wishlist.total_price = float(wishlist.total_price) - float(price)
                    wishlist.items.pop(wishlist.items.index(item))
                    wishlist.updated_at = today
                    wishlist.save()

                return Response({"result": "success", "message": "Your cart is create successfully", "content": serializer},
                                status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return Response({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return Response({"result": "error", "message": "Record is not found."},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while carting: %s", e)
            return Response({"result": "error", "message": "Error occurred while carting"},
                            status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["E-commerce Users"],
        responses={200: dict},
        description="E-commerce view set"
    )
    @action(detail=False, methods=['get'], url_path='get-cart-items')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def get_cart_items(self, request):
        try:
            # Get cart of the current user
            user = get_object_or_404(CustomUser.objects, email=request.user)
            cart = get_object_or_404(Cart.objects, owner=user)

            cart_response = {
                "items": [],
                "total_price": 0
            }

            for item in cart.items:
                index = cart.items.index(item)

                # Get item info
                cart_item = get_object_or_404(Item.objects, _id=item)

                temp_data = {
                    "_id": cart_item._id,
                    "name": capwords(cart_item.name),
                    "thumbnail": cart_item.thumbnail,
                    "quantity": cart.quantity[index],
                    "color": cart.color[index],
                    "measurement": cart.measurement[index],
                    "price": cart_item.price
                }
                cart_response["items"].append(temp_data)

            cart_response["total_price"] = cart.total_price

            return JsonResponse({"result": "success", "message": "Fetch cart items", "content": cart_response}, status=status.HTTP_200_OK)

        except Http404:
            return Response({"result": "error", "message": "Record is not found."},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching cart: %s", e)
            return Response({"result": "error", "message": "Error occurred while fetching cart"},
                            status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["E-commerce Users"],
        responses={200: dict},
        description="E-commerce view set"
    )
    @action(detail=False, methods=['delete'], url_path='delete-cart-item')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def delete_cart_item(self, request):
        try:
            item = request.query_params.get("id")

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)

                cart = get_object_or_404(Cart.objects, owner=user)

                if not item in cart.items:
                    raise ValueErrorException("Item is not found in your cart")

                cart_item = get_object_or_404(Item.objects, _id=item)

                price = cart_item.price
                # get item quantity
                index = cart.items.index(item)
                quantity = cart.quantity[index]
                cart.total_price = float(cart.total_price) - (float(price) * int(quantity))

                cart.items.pop(index)
                cart.quantity.pop(index)
                cart.measurement.pop(index)
                cart.color.pop(index)

                cart.record_time = today
                cart.save()

                serializer = ItemCartSerializer(cart).data

                return JsonResponse({"result": "success", "message": "Item is removed successfully", "content": serializer},
                                    status=status.HTTP_200_OK)

        except ValueErrorException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting item from cart: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting item from cart"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["E-commerce Users"],
        responses={200: dict},
        description="E-commerce view set"
    )
    @action(detail=False, methods=['post'], url_path='add-to-wishlist')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def add_wishlist(self, request):
        try:
            item = request.query_params.get("id")

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)

                selected_item = get_object_or_404(Item.objects, _id=item)
                wishlist = Wishlist.objects.filter(owner=user).first()

                if wishlist:
                    if item in wishlist.items:
                        return JsonResponse(
                            {"result": "success", "message": "The item is already in your wishlist",},
                            status=status.HTTP_200_OK)

                    price = Item.objects.get(_id=item).price
                    wishlist.items.append(item)
                    wishlist.total_price = float(wishlist.total_price) + float(price)
                    wishlist.updated_at = today
                    wishlist.record_time = today
                    wishlist.save()

                    serializer = ItemWishlistSerializer(wishlist).data

                    return JsonResponse(
                        {"result": "success", "message": "Your wishlist is updated successfully", "content": serializer},
                        status=status.HTTP_200_OK)

                items_list = []
                total_price = 0.00
                price = Item.objects.get(_id=item).price
                total_price = float(total_price) + float(price)
                items_list.append(item)
                wishlist = Wishlist.objects.create(
                    owner=user,
                    items=items_list,
                    total_price=str(total_price),
                    created_at=today,
                    updated_at=today,
                    record_time=today
                )
                wishlist.save()

                serializer = ItemWishlistSerializer(wishlist).data

                return JsonResponse({"result": "success", "message": "Your wishlist is create successfully", "content": serializer},
                                    status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while wish listing: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while wish listing"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["E-commerce Users"],
        responses={200: dict},
        description="E-commerce view set"
    )
    @action(detail=False, methods=['get'], url_path='get-wishlist-items')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def get_wishlist_items(self, request):
        try:
            # Get cart of the current user
            user = get_object_or_404(CustomUser.objects, email=request.user)
            wishlist = get_object_or_404(Wishlist.objects, owner=user)

            wishlist_response = {
                "items": [],
                "total_price": 0
            }

            for item in wishlist.items:
                # Get item info
                wishlist_item = get_object_or_404(Item.objects, _id=item)

                temp_data = {
                    "_id": wishlist_item._id,
                    "name": capwords(wishlist_item.name),
                    "thumbnail": wishlist_item.thumbnail,
                    "price": wishlist_item.price,
                }
                wishlist_response["items"].append(temp_data)

            wishlist_response["total_price"] = wishlist.total_price

            return JsonResponse({"result": "success", "message": "Fetch wishlist items", "content": wishlist_response},
                                status=status.HTTP_200_OK)

        except Http404:
            return Response({"result": "error", "message": "Record is not found."},
                            status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching wish listing: %s", e)
            return Response({"result": "error", "message": "Error occurred while fetching wish listing"},
                            status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["E-commerce Users"],
        responses={200: dict},
        description="E-commerce view set"
    )
    @action(detail=False, methods=['delete'], url_path='delete-wishlist-item')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def delete_wishlist_item(self, request):
        try:
            item = request.query_params.get("id")

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)
                wishlist = get_object_or_404(Wishlist.objects, owner=user)
                wishlist_item = get_object_or_404(Item.objects, _id=item)

                if not item in wishlist.items:
                    raise ValueErrorException("Item is not found in your wishlist")

                price = wishlist_item.price
                # get item quantity
                index = wishlist.items.index(item)
                wishlist.total_price = float(wishlist.total_price) - float(price)

                wishlist.items.pop(index)

                wishlist.record_time = today
                wishlist.save()

                serializer = ItemWishlistSerializer(wishlist).data

                return JsonResponse({"result": "success", "message": "Item is removed successfully", "content": serializer},
                                    status=status.HTTP_200_OK)

        except ValueErrorException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting item from wishlist item: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting item from wishlist item"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["E-commerce Users"],
        request=AddItemReviewSerializer,
        responses={200: dict},
        description="E-commerce view set"
    )
    @action(detail=False, methods=['post'], url_path='add-item-review')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def add_item_review(self, request):
        serializer = AddItemReviewSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            item = serializer.validated_data["item"]
            rate = serializer.validated_data["rate"]
            review = serializer.validated_data["review"]

            # Value Validation
            validator = ToCartDataValidator(serializer.validated_data,
                                            fields=["item"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)

                selected_item = get_object_or_404(Item.objects, _id=item)

                if int(rate) < 0 or int(rate) > 5:
                    raise ValueErrorException("Review rate is invalid")

                user_review = ItemReview.objects.filter(active_user=user).first()
                if user_review:
                    if rate != '':
                        user_review.rate = rate
                    if review != '':
                        user_review.review = review
                    user_review.updated_at = today
                    user_review.record_time = today
                    user_review.save()

                    return JsonResponse({"result": "success", "message": "Item review is submitted successfully"}, status=status.HTTP_200_OK)

                review = ItemReview.objects.create(
                    active_user=user,
                    item=selected_item,
                    rate=rate,
                    review=review,
                    created_at=today,
                    updated_at=today
                )
                review.save()

                return JsonResponse({"result": "success", "message": "Item review is submitted successfully"}, status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while review item: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while review item"},
                                status=status.HTTP_400_BAD_REQUEST)

class PaymentConfirmationViewSet(viewsets.ViewSet):
    """
    Payment confirmation view set
    """

    @extend_schema(
        tags=["Payment Confirmation Order"],
        responses={200: dict},
        description="Payment methods list"
    )
    @action(detail=False, methods=['get'], url_path='get-payment-methods')
    def get_payment_methods(self, request):
        try:
            methods = PaymentMethod.objects.all().order_by("-record_time")

            if not methods:
                raise Http404

            response = []
            for method in methods:
                serializer = PaymentMethodSerializer(method).data
                response.append(serializer)

            return JsonResponse(
                {"result": "success", "message": "Payment methods list", "content": response},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Payment methods are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching payment methods: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching payment methods."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Payment Confirmation Order"],
        request=PaymentConfirmationOrderEcommerceSerializer,
        responses={200: dict},
        description="Payment confirmation view set. Ecommerce payment confirmation is like checkout carted items"
    )
    @action(detail=False, methods=['post'], url_path='add-ecommerce-pc')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def add_ecommerce_pc(self, request):
        serializer = PaymentConfirmationOrderEcommerceSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            name = serializer.validated_data.get("name")
            email = serializer.validated_data.get("email").lower()
            phone = serializer.validated_data.get("phone")
            method = serializer.validated_data.get("method")
            proof = serializer.validated_data.get("proof")

            # Value Validation
            validator = EcommercePCValidator(serializer.validated_data,
                                            fields=["name", "email", "phone", "method", "proof"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)

                if user.email != email.lower():
                    raise ValueErrorException("Failed to request payment confirmation approval. Use your account email.")

                selected_method = get_object_or_404(PaymentMethod.objects, _id=method)
                cart = get_object_or_404(Cart.objects, owner=user)

                order_id = 0
                file_name = str(uuid.uuid4())
                if proof is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "PC/ecommerce",
                                             file_name + '.' + proof.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in proof.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + proof.name.split('.')[-1]

                # Generate order ID
                while 1:
                    random_number = random.randint(10000, 99999)
                    if EcommercePC.objects.filter(order_id=random_number).exists():
                        continue
                    else:
                        order_id = random_number
                        break

                pc = EcommercePC.objects.create(
                    order_id=order_id,
                    user_name=user,
                    user_email=email,
                    user_phone=phone,
                    items=cart.items,
                    quantity=cart.quantity,
                    total_price=cart.total_price,
                    proof=file_name,
                    method=selected_method,
                    created_at=today,
                    updated_at=today
                )
                pc.save()

                serializer = EcommercePCSerializer(pc).data

                return JsonResponse({"result": "success", "message": "Payment confirmation is added successfully", "content": serializer},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while adding PC: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while adding PC"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Payment Confirmation Order"],
        request=PackagePCOrderSerializer,
        responses={200: dict},
        description="Payment confirmation view set"
    )
    @action(detail=False, methods=['post'], url_path='add-package-pc')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def add_package_pc(self, request):
        serializer = PackagePCOrderSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            email = serializer.validated_data.get("email").lower()
            plan = serializer.validated_data.get("plan")
            method = serializer.validated_data.get("method")
            proof = serializer.validated_data.get("proof")

            # Value Validation
            validator = PackagePCValidator(serializer.validated_data,
                                            fields=["email", "plan", "method", "proof"])
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)

                if user.email != email.lower():
                    raise ValueErrorException("Use your account email to process subscription")

                package_plan = get_object_or_404(Package.objects, _id=plan)
                payment_method = get_object_or_404(PaymentMethod.objects, _id=method)

                if PackagePC.objects.filter(Q(user=user) & Q(package=package_plan)).exists():
                    raise ValueDuplicationException("You have already subscribed to the package but your payment confirmation is on process.")

                if PackagePC.objects.filter(Q(user=user) & Q(status='approved')).exists():
                    raise ValueDuplicationException("You've active subscription package. Use another account to use other subscription.")

                file_name = str(uuid.uuid4())
                if proof is not None:
                    file_path = os.path.join(settings.MEDIA_ROOT, "PC/package",
                                             file_name + '.' + proof.name.split('.')[-1])
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'wb+') as destination:
                        for chunk in proof.chunks():
                            destination.write(chunk)
                    file_name = file_name + '.' + proof.name.split('.')[-1]

                pc = PackagePC.objects.create(
                    package=package_plan,
                    user=user,
                    price=package_plan.price,
                    proof=file_name,
                    method=payment_method,
                    created_at=today,
                    updated_at=today
                )
                pc.save()

                serializer = PackagePCSerializer(pc).data

                return JsonResponse({"result": "success", "message": "Subscription payment confirmation is added successfully", "content": serializer},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueErrorException, ValueDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while adding subscription PC: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while adding subscription PC"},
                                status=status.HTTP_400_BAD_REQUEST)

class CourseViewSet(viewsets.ViewSet):
    """
    Course view set
    """
    @extend_schema(
        tags=["Course Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-course-categories')
    def get_course_categories(self, request):
        try:
            categories = CourseCategory.objects.all().order_by("-record_time")

            if not categories:
                raise Http404

            paginator = CourseDataPagination()
            categories_list = paginator.paginate_course_categories(request, categories)

            return JsonResponse(
                {"result": "success", "message": "Course categories list", "content": categories_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Course categories is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching course categories: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching course categories."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Course Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-courses')
    def get_courses(self, request):
        try:
            courses = Course.objects.all().order_by("-record_time")

            if not courses:
                raise Http404

            paginator = CourseDataPagination()
            courses_list = paginator.paginate_courses(request, courses)

            return JsonResponse({"result": "success", "message": "Courses list", "content": courses_list.data['results']},
                                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Courses is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching courses: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching courses."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Course Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-course')
    def get_course(self, request):
        try:
            _id = request.query_params.get("id")
            get_course = get_object_or_404(Course.objects, _id=_id)

            lessons = CourseLesson.objects.filter(course=get_course).all()

            # response structure course info + lessons + meal plans
            response = {
                "isSubscribed": "false",
                "category": {},
                "course": {},
                "lessons": [],
                "meal_plans": [],
            }

            # check if the logged user is subscribed to package
            if request.user.is_authenticated:
                logged_user = CustomUser.objects.filter(email=request.user).first()
                user = CustomUsers.objects.filter(user=logged_user).first()

                if "course" in user.package:
                    response["isSubscribed"] = "true"

            # Get course category
            category = CourseCategory.objects.filter(_id=get_course.category._id).first()
            if category:
                response["category"] = {
                    "name": capwords(category.name),
                    "color": category.color,
                    "icon": category.icon
                }
            else:
                response["category"] = {
                    "name": "Uncategorized",
                    "color": "#000",
                    "icon": ""
                }

            # Get the course response
            response["course"] = {
                "title": capwords(get_course.title),
                "thumbnail": get_course.thumbnail,
                "overview": get_course.overview,
                "description": get_course.description,
                "objectives": get_course.objectives,
                "intro": get_course.intro,
                "total_duration": get_course.total_duration,
                "level": get_course.level,
                "isCertificated": get_course.is_certificated,
                "language": get_course.language,
            }

            lessons_response = []
            # Get the lessons under the course
            for lesson in lessons:
                temp_data = {
                    "_id": lesson._id,
                    "title": capwords(lesson.title),
                    "thumbnail": lesson.thumbnail,
                    "duration": lesson.duration,
                    "description": lesson.description,
                    "video_id": lesson.video_id
                }
                lessons_response.append(temp_data)

            response["lessons"] = lessons_response

            meal_plans_response = []
            # Get meal plans associated with the course
            meal_plans = MealPlan.objects.filter(course=get_course).all()
            for meal_plan in meal_plans:
                temp_data = {
                    "_id": meal_plan._id,
                    "name": capwords(meal_plans.name),
                    "overview": capwords(meal_plans.overview),
                    "course": get_course,
                    "course_name": capwords(get_course.title),
                    "thumbnail": meal_plan.thumbnail,
                    "recipe_count": meal_plan.recipe_count
                }
                meal_plans_response.append(temp_data)

            response["meal_plans"] = meal_plans_response

            return JsonResponse({"result": "success", "message": "Course list", "content": response},
                                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Course is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching course: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching course."},
                                status=status.HTTP_400_BAD_REQUEST)

class MealPlanViewSet(viewsets.ViewSet):
    """
    Meal plans view a set
    """
    @extend_schema(
        tags=["Meal Plan Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-meal-plans')
    def get_meal_plans(self, request):
        try:
            meal_plans = MealPlan.objects.all().order_by("-record_time")

            if not meal_plans:
                raise Http404

            paginator = MealPlanDataPagination()
            meal_plans_list = paginator.paginate_meal_plan(request, meal_plans)

            return JsonResponse(
                {"result": "success", "message": "Meal plans list", "content": meal_plans_list.data['results']},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Meal plans is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching meal plans: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching meal plans."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Meal Plan Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-meal-plan')
    def get_meal_plan(self, request):
        try:
            _id = request.query_params.get("id")
            get_meal_plan = get_object_or_404(MealPlan.objects, _id=_id)

            recipes = MealPlanRecipe.objects.filter(meal=get_meal_plan).all()

            # response structure meal plan and recipes
            response = {
                "isSubscribed": "false",
                "meal_plans": {},
                "recipes": [],
            }

            # check if the logged user is subscribed to package
            if request.user.is_authenticated:
                logged_user = CustomUser.objects.filter(email=request.user).first()
                user = CustomUsers.objects.filter(user=logged_user).first()

                if "meal plan" in user.package:
                    response["isSubscribed"] = "true"

            # Get the meal plan's course
            course = Course.objects.filter(_id=get_meal_plan.course._id).first()
            course_name = ""
            if course:
                course_name = course.title

            # Get the meal plan response
            response["meal_plans"] = {
                "_id": get_meal_plan._id,
                "name": capwords(get_meal_plan.name),
                "overview": get_meal_plan.overview,
                "description": get_meal_plan.description,
                "course": capwords(course_name),
                "thumbnail": get_meal_plan.thumbnail,
                "intro": get_meal_plan.intro,
                "recipe_count": get_meal_plan.recipe_count,
            }

            # Get the recipes under meal plans
            recipes_response = []
            for recipe in recipes:
                temp_data = {
                    "_id": recipe._id,
                    "name": capwords(recipe.name),
                    "thumbnail": recipe.thumbnail,
                    "duration": recipe.duration,
                    "description": recipe.description,
                    "video_link": recipe.video_link
                }
                recipes_response.append(temp_data)

            response["recipes"] = recipes_response

            return JsonResponse({"result": "success", "message": "Meal plan", "content": response},
                                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Meal plan is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching meal plan: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching meal plan."},
                                status=status.HTTP_400_BAD_REQUEST)

class AudioBookViewSet(viewsets.ViewSet):
    """
    Audiobook view set
    """
    @extend_schema(
        tags=["Audiobook Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-audio-books-categories')
    def get_audio_books_categories(self, request):
        try:
            categories = AudiobookCategory.objects.all().order_by("-record_time")

            if not categories:
                raise Http404

            paginator = AudiobookCategoryDataPagination()
            categories_list = paginator.paginate_audiobook_category(request, categories)

            return JsonResponse(
                {"result": "success", "message": "Audiobook categories list", "content": categories_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Audiobook categories is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching audio books categories: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching audio book categories."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["AudioBook Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-audio-books')
    def get_audio_books(self, request):
        try:
            audio_books = Audiobook.objects.all().order_by("-record_time")

            if not audio_books:
                raise Http404

            paginator = AudiobookDataPagination()
            audio_books_list = paginator.paginate_audiobook(request, audio_books)

            return JsonResponse(
                {"result": "success", "message": "Audiobooks list", "content": audio_books_list.data['results']},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Audiobooks is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching audiobooks: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching audiobooks."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-audio-book')
    def get_audio_book(self, request):
        try:
            _id = request.query_params.get("id")
            get_audio_book = get_object_or_404(Audiobook.objects, _id=_id)

            # response structure
            response = {
                "isSubscribed": "false",
                "audio_book": {}
            }

            # check if the logged user is subscribed to package
            if request.user.is_authenticated:
                logged_user = CustomUser.objects.filter(email=request.user).first()
                user = CustomUsers.objects.filter(user=logged_user).first()

                if "audio book" in user["package"]:
                    response["isSubscribed"] = "true"

            audio_book_category = AudiobookCategory.objects.filter(_id=get_audio_book.category._id).first()
            category_name = capwords(audio_book_category.name) if audio_book_category else "UNCATEGORIZED"

            # Get the audiobook response
            response["audio_book"] = {
                "_id": get_audio_book._id,
                "title": capwords(get_audio_book.title),
                "category": category_name,
                "overview": get_audio_book.overview,
                "description": get_audio_book.description,
                "audio": get_audio_book.audio,
                "sliced_audio": get_audio_book.sliced_audio,
                "duration": get_audio_book.duration,
                "thumbnail": get_audio_book.thumbnail,
            }

            return JsonResponse({"result": "success", "message": "Audiobook", "content": response},
                                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Audiobook is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching audiobook: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching audiobook."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook Users"],
        request=CreatePlaylistSerializer,
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['post'], url_path='add-update-playlist')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def create_playlist(self, request):
        serializer = CreatePlaylistSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            name = serializer.validated_data.get("name").lower()
            audios = serializer.validated_data.get("audios")

            # Value Validation
            validator = PlaylistDataValidator(serializer.validated_data,
                                             fields=["name", "audios"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)

                if Playlist.objects.filter(Q(user=user) & Q(name=name)).exists():
                    raise ValueDuplicationException("Playlist name is already found.")

                if len(audios) <= 0:
                    raise ValueErrorException("No audios given to add in playlist")

                # Fetch valid audiobooks
                compare_existing_audio_ids = set(
                    Audiobook.objects.filter(_id__in=audios, is_deleted=False).values_list('_id', flat=True)
                )
                existing_audio_ids = {str(i) for i in compare_existing_audio_ids}

                # Find missing ones
                missing_audio_ids = set(audios) - existing_audio_ids

                if missing_audio_ids:
                    raise ValueErrorException(f"The following audio IDs were not found: {', '.join(missing_audio_ids)}")

                # remove duplication
                audios_unique_list = list(dict.fromkeys(existing_audio_ids))

                # Create playlist
                playlist = Playlist.objects.create(
                    user=user,
                    name=name,
                    audios=audios_unique_list,
                    created_at=today,
                    updated_at=today
                )
                playlist.save()

                serializer = PlaylistSerializer(playlist).data

                return JsonResponse({"result": "success", "message": "Your playlist is created successfully",
                                     "content": serializer},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueDuplicationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating playlist: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating playlist"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook Users"],
        request=AddAudioToPlaylistSerializer,
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['patch'], url_path='add-audio-playlist')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def add_audio_to_playlist(self, request):
        serializer = AddAudioToPlaylistSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            _id = serializer.validated_data.get("_id")
            audios = serializer.validated_data.get("audios")

            # Value Validation
            validator = PlaylistDataValidator(serializer.validated_data,
                                              fields=["audios"], null_validation=False)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)
                playlist = get_object_or_404(Playlist.objects, _id=_id)

                if user != playlist.user:
                    raise Http404

                if len(audios) <= 0:
                    return JsonResponse({"result": "success", "message": "No audios added", "content": ""}, status=status.HTTP_200_OK)

                # Fetch valid audiobooks
                compare_existing_audio_ids = set(
                    Audiobook.objects.filter(_id__in=audios, is_deleted=False).values_list('_id', flat=True)
                )
                existing_audio_ids = {str(i) for i in compare_existing_audio_ids}

                # Find missing ones
                missing_audio_ids = set(audios) - existing_audio_ids

                if missing_audio_ids:
                    raise ValueErrorException(f"The following audio IDs were not found: {', '.join(missing_audio_ids)}")

                # remove duplication
                audios_unique_list = list(dict.fromkeys(existing_audio_ids))

                # compare incoming audio list with the existing ones without duplication
                combined_unique_audios = list(dict.fromkeys(playlist.audios + audios_unique_list)) if playlist.audios is not None or playlist.audios != [] else audios_unique_list

                playlist.audios = combined_unique_audios
                playlist.save()

                serializer = PlaylistSerializer(playlist).data

                return JsonResponse({"result": "success", "message": "Your playlist is updated successfully",
                                     "content": serializer},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating playlist: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating playlist"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-user-playlists')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def get_user_playlists(self, request):
        try:
            user = get_object_or_404(CustomUser.objects, username=request.user)
            playlists = Playlist.objects.filter(user=user).all().order_by("-record_time")

            if not playlists:
                raise Http404

            paginator = PlaylistDataPagination()
            playlists_list = paginator.paginate_playlist(request, playlists)

            return JsonResponse(
                {"result": "success", "message": "Playlists list", "content": playlists_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Playlists are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching playlists: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching playlists."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-user-playlist')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def get_user_playlist(self, request):
        try:
            _id = request.query_params.get("id")
            user = get_object_or_404(CustomUser.objects, username=request.user)
            playlist = get_object_or_404(Playlist.objects, _id=_id)

            if user != playlist.user:
                raise Http404

            serializer = GetAllPlaylistsSerializer(playlist).data

            return JsonResponse(
                {"result": "success", "message": "Playlist details", "content": serializer},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Playlist is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching playlist: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching playlist."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['delete'], url_path='remove-audio-playlist')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def remove_audio_from_playlist(self, request):
        _id = request.query_params.get("id") # playlist id
        audio = request.query_params.get("audio") # audio id

        try:
            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)
                playlist = get_object_or_404(Playlist.objects, _id=_id)
                audio = get_object_or_404(Audiobook.objects, _id=audio)

                if user != playlist.user:
                    raise Http404

                playlist.audios = [aid for aid in playlist.audios if aid != str(audio)]
                playlist.save()

                serializer = PlaylistSerializer(playlist).data

                return JsonResponse({"result": "success", "message": "Audiobook is removed from your playlist successfully",
                                     "content": serializer},
                                    status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while removing audiobook from playlist: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while removing audiobook from playlist"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Audiobook Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['delete'], url_path='delete-playlist')
    @permission_classes([IsAuthenticated, role_required(["user"])])
    def delete_playlist(self, request):
        _id = request.query_params.get("id")  # playlist id

        try:
            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)
                playlist = get_object_or_404(Playlist.objects, _id=_id)

                if user != playlist.user:
                    raise Http404

                playlist.delete()

                return JsonResponse(
                    {"result": "success", "message": "Your playlist is deleted successfully",
                     "content": ""},
                    status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while removing deleting playlist: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting playlist"},
                                status=status.HTTP_400_BAD_REQUEST)

class PackagePlanViewSet(viewsets.ViewSet):
    """
    Package plan view set
    """
    @extend_schema(
        tags=["Package Plan Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-package-plans')
    def get_package_plans(self, request):
        try:
            plans = Package.objects.all().order_by("-record_time")

            if not plans:
                raise Http404

            paginator = PackagePlanDataPagination()
            plans_list = paginator.paginate_package(request, plans)

            return JsonResponse(
                {"result": "success", "message": "Package plans list", "content": plans_list.data},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Package plan is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching package plans: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching package plans."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Package Plan Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-package-plan')
    def get_package_plan(self, request):
        try:
            _id = request.query_params.get("id")
            get_package_plan = get_object_or_404(Package.objects, _id=_id)

            serializer = PackagePlanSerializer(get_package_plan).data

            return JsonResponse({"result": "success", "message": "Package plan", "content": serializer},
                                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Package plan is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching package plan: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching package plan."},
                                status=status.HTTP_400_BAD_REQUEST)

class CustomerSubscriptionViewSet(viewsets.ViewSet):
    """
    1. Check if given user is subscribed to given package
    2. Get package that given user is subscribed
    """
    @extend_schema(
        tags=["Customer Subscription"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='check-subscription')
    def check_subscription(self, request):
        try:
            customer = request.query_params.get("customer")
            package = request.query_params.get("package")

            get_package_plan = get_object_or_404(Package.objects, _id=package)
            get_user = get_object_or_404(CustomUser.objects, id=customer)

            # Check the given user is subscribed to the given package
            package_pc = PackagePC.objects.filter(user=get_user, package=get_package_plan).first()

            if not package_pc:
                raise ValueErrorException("No subscription is found.")

            serializer = PackagePCSerializer(package_pc).data

            return JsonResponse({"result": "success", "message": "You're subscribed to the package.", "content": serializer},
                                status=status.HTTP_200_OK)

        except ValueErrorException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)

        except Http404:
            return JsonResponse({"result": "error", "message": "Resource is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while checking subscription: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while checking subscription."},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Customer Subscription"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-user-subscription')
    def get_user_subscription(self, request):
        try:
            customer = request.query_params.get("customer")

            get_user = get_object_or_404(CustomUser.objects, id=customer)

            # Get user subscription for package pc
            package_pc = PackagePC.objects.filter(user=get_user).first()

            if not package_pc:
                raise ValueErrorException("No subscription is found.")

            serializer = PackagePCSerializer(package_pc).data

            return JsonResponse(
                {"result": "success", "message": "You've subscribed to a package.", "content": serializer},
                status=status.HTTP_200_OK)

        except ValueErrorException as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)

        except Http404:
            return JsonResponse({"result": "error", "message": "Resource is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while getting user subscription: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while getting user subscription."},
                                status=status.HTTP_400_BAD_REQUEST)
