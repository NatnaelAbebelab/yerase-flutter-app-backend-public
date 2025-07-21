import logging
import os
import random
import requests
import secrets
import string
from datetime import date

from rest_framework import viewsets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models.functions import Cast
from django.db.models import Q, F, Sum, IntegerField
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .utility.token import get_tokens_for_user
from rest_framework.decorators import permission_classes, action
from rest_framework.response import Response
from string import capwords

from utils.exceptions import *
from utils.permissions import role_required
from .models import CustomUsers
from .requestSerializers import *
from .services.validations import *
from .services.pagination import *

# Create your views here.
logger = logging.getLogger(__name__)
today = date.today()
User = get_user_model()

"""
These are class based view to execute operation
"""
def generate_temp_password(length):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for _ in range(length))
def generate_otp():
    return str(random.randint(100000, 999999))

#===================> Account Class based Views <=============================

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
            gender = serializer.validated_data["gender"]

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

                otp_code = '0'
                while True:
                    otp_code = generate_otp()
                    if customers.filter(otp_code=otp_code).count() > 0:
                        continue
                    else:
                        break

                user = CustomUser.objects.create(
                    first_name=fname,
                    last_name=lname,
                    username=email,
                    email=email,
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

                # send email notification / OTP
                context = {
                    'fname': fname.capitalize(),
                    'lname': lname.capitalize(),
                    'email': email,
                    'activation_link': 'http://localhost:8000/activate/' + otp_code
                }
                template = get_template('add-customer-email-template.html')
                message_content = template.render(context)
                subject = 'Activate Your Account'
                message = message_content
                email = EmailMessage(subject, message, 'natnaelabebelab@gmail.com', [email])
                email.content_subtype = 'html'
                email.send()

                return Response(
                    {"result": "success", "message": "You have signed up successfully.", "content": customer},
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
            email = serializer.validated_data["email"]
            password = serializer.validated_data["password"]

            # Value Validation
            validator = AccountActivationDataValidator(serializer.validated_data,
                                                       fields=["otp_code", "email", "password"],
                                                       null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                if not CustomUsers.objects.filter(otp_code=otp_code).exists():
                    raise ValueErrorException("OTP code is not found")
                if not CustomUser.objects.filter(email=email.lower()).exists():
                    raise ValueErrorException("Email address is not found")

                user = get_object_or_404(CustomUser.objects, email=email.lower())
                customer = get_object_or_404(CustomUsers.objects, user=user)

                if check_password(password, user.password):
                    customer.otp_code = '1'
                    customer.save()
                    if user.email == email.lower() and user.username == email.lower():
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

            email = serializer.validated_data["email"]
            password = serializer.validated_data["password"]

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

                user = get_object_or_404(CustomUser.objects, email=email.lower())
                customer = get_object_or_404(CustomUsers.objects, user=user)

                if customer.otp_code != '1':
                    raise ValueErrorException("Your account is not activated")

                if check_password(password, user.password):
                    login(request, user)
                    tokens = get_tokens_for_user(user)
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
                customer = get_object_or_404(CustomUsers.objects, user=user)

                # generate password
                temp_password = generate_temp_password(8)
                reset_code = '0'
                while 1:
                    reset_code = generate_otp()
                    if CustomUsers.objects.filter(reset_code=reset_code).count() > 0:
                        continue
                    else:
                        break
                user.password = make_password(temp_password)
                user.save()
                customer.reset_code = reset_code
                customer.save()

                context = {
                    'fname': user.fname.capitalize(),
                    'lname': user.lname.capitalize(),
                    'email': user.email,
                    'reset_link': 'http://localhost:8000/reset/' + reset_code
                }
                template = get_template('add-customer-reset-template.html')
                message_content = template.render(context)
                subject = 'Reset Your Password'
                message = message_content
                email = EmailMessage(subject, message, 'natnaelabebelab@gmail.com', [email])
                email.content_subtype = 'html'  # Specify that the email content is HTML
                email.send()

                return JsonResponse({"result": "success", "message": "You've reset your password"},
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

    #@permission_classes([IsAuthenticated, role_required(["user"])])
    @extend_schema(
        tags=["Customer Accounts"],
        request=UpdateAccountProfileSerializer,
        responses={200: dict},
        description="Reset your password"
    )
    @action(detail=False, methods=['patch'], url_path='update-account')
    def update_account(self, request):
        serializer = UpdateAccountProfileSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            fname = serializer.validated_data["fname"]
            lname = serializer.validated_data["lname"]
            email = serializer.validated_data["email"]
            phone = serializer.validated_data["phone"]
            weight = serializer.validated_data["weight"]
            height = serializer.validated_data["height"]
            age = serializer.validated_data["age"]
            gender = serializer.validated_data["gender"]
            profile = serializer.validated_data["profile"]

            # Value Validation
            validator = UserAccountDataValidator(serializer.validated_data,
                                                 fields=["fname", "lname", "email", "phone", "weight", "height", "age",
                                                         "gender"])
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

                if CustomUser.objects.filter(Q(email=email.lower())) and email.lower() != request.user:
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
                    user.fname = fname
                if lname:
                    user.lname = lname
                if email:
                    user.email = email.lower()
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

                return JsonResponse({"result": "success", "message": "You've updated your profile"},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while updating profile: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while updating profile"},
                                status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Customer Accounts"],
        request=ChangePasswordSerializer,
        responses={200: dict},
        description="Change your password"
    )
    @action(detail=False, methods=['patch'], url_path='change-password')
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            current = serializer.validated_data["current"]  # current password of logged user
            password = serializer.validated_data["new"]

            # Value Validation
            validator = UserAccountDataValidator(serializer.validated_data,
                                                 fields=["password"])
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)
                if not check_password(current, user.password):
                    raise ValueErrorException("Your current password doesn't match")

                # Current password match so update it by the new password
                user.password = make_password(password)
                user.save()

                return JsonResponse({"result": "success", "message": "You've updated your password"},
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

class AppointmentViewSet(viewsets.ViewSet):
    """
    Appointment view set to book virtual meeting
    """

    # @permission_classes([IsAuthenticated, RoleBasedPermission])  # Use your custom permission
    # @role_required("user")
    @extend_schema(
        tags=["Appointment User"],
        request=BookAppointmentSerializer,
        responses={200: dict},
        description="Change your password"
    )
    @action(detail=False, methods=['post'], url_path='schedule-appointment')
    def schedule_appointment(self, request):
        serializer = BookAppointmentSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            subject = serializer.validated_data["subject"]
            message = serializer.validated_data["message"]
            schedule = serializer.validated_data["schedule"]

            # Value Validation
            validator = AppointmentDataValidator(serializer.validated_data,
                                                 fields=["subject", "message", "schedule"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)

                today_date = date.today()
                schedule_date = datetime.strptime(schedule, "%Y-%m-%d").date()

                if schedule_date < today_date:
                    raise ValueErrorException("Reservation schedule must be in the coming days")

                appointment = Appointment.objects.create(
                    customer=user.email,
                    subject=subject,
                    message=message,
                    schedule=schedule,
                    created_at=today,
                    update_at=today,
                )
                appointment.save()

                return JsonResponse({"result": "success", "message": "You've requested appointment successfully"},
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

class EcommerceViewSet(viewsets.ViewSet):
    """
    Ecommerce view to access store
    """

    # @permission_classes([IsAuthenticated, role_required("user")])
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

    # @permission_classes([IsAuthenticated, role_required("user")])
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

            response = {
                "items": []
            }

            for item in items_list.data:
                temp_data = []

                category = ItemCategory.objects.filter(_id=item.category)
                category_name = capwords(category.name) if category else "UNCATEGORIZED"
                temp_data.append(category_name)

                temp_data.append(item)

                response["items"].append(temp_data)

            return JsonResponse(
                {"result": "success", "message": "Items list", "content": response},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Items are not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching items: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching items."},
                                status=status.HTTP_400_BAD_REQUEST)

    # @permission_classes([IsAuthenticated, role_required("user")])
    @extend_schema(
        tags=["E-commerce Users"],
        responses={200: dict},
        description="Get a specific item by ID"
    )
    @action(detail=False, methods=['get'], url_path='get-item/(?P<_id>[^/.]+)')
    def get_item(self, request, _id=None):
        try:
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

            category = ItemCategory.objects.filter(_id=item.category)
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
                'size': 'display-none',
                'quantity': 'display-none',
                'type': 'free',
                'min': '0',
                'max': '0'
            }

            if category.measurement == 'l':
                measurement['quantity'] = 'display-block'
                measurement['type'] = 'Liter'  # Fixed typo
                measurement['min'] = str(item.min_value)  # Ensure string
                measurement['max'] = str(item.max_value)  # Ensure string
            elif category.measurement == 'kg':
                measurement['quantity'] = 'display-block'
                measurement['type'] = 'Mass'
                measurement['min'] = str(item.min_value)  # Ensure string
                measurement['max'] = str(item.max_value)  # Ensure string
            elif category.measurement == 's':
                measurement['size'] = 'display-block'
                measurement['type'] = 'Size'
            else:
                logger.error(f"Unknown measurement type '{category.measurement}' for category {category.name}")

            response["measurement"] = measurement

            # Get item review
            item_review = ItemReview.objects.filter(item=item._id)
            total_rate = item_review.aggregate(total_rate=Sum(Cast('rate', IntegerField())))['total_rate']
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
            item_review = item_review.filter(~Q(active_user=request.user))
            for r in item_review[:4]:
                data = {
                    "review_id": r._id,
                    "photo": "user-11.jpg",
                    "fullname": "Customer",
                    "div": "d-md-flex",
                    "display": "display-block",
                    "review": r.review,
                    "rate": ['item'] * int(r.rate)
                }
                response['reviews'][str(r._id)] = data

            # Get current users
            current_user_review = item_review.filter(Q(active_user=request.user) & Q(status='publish')).first()
            if current_user_review and CustomUser.objects.filter(email=request.user).exists():
                c = CustomUser.objects.get(email=request.user)
                response["user_review"]['photo'] = c.profile
                response["user_review"]['fullname'] = string.capwords(c.fname) + ' ' + string.capwords(c.lname)
                response["user_review"]['div'] = 'd-md-flex'
                response["user_review"]['display'] = 'display-block'
                response["user_review"]['review'] = current_user_review.review
                response["user_review"]['rate'] = ['item'] * int(current_user_review.rate)

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

    #@permission_classes([IsAuthenticated, role_required("user")])
    @extend_schema(
        tags=["E-commerce Users"],
        request=AddToCartSerializer,
        responses={200: dict},
        description="E-commerce view set"
    )
    @action(detail=False, methods=['post'], url_path='add-to-cart')
    def add_to_cart(self, request):
        serializer = AddToCartSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            item = serializer.validated_data["item"]
            quantity = serializer.validated_data["quantity"]
            color = serializer.validated_data["color"]
            measurement = serializer.validated_data["measurement"]

            # Value Validation
            validator = ToCartDataValidator(serializer.validated_data,
                                            fields=["item", "quantity", "color", "measurement"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)

                cart = Cart.objects.filter(owner=user.email).first();
                wishlist = Wishlist.objects.filter(owner=user.email).first()

                if cart:
                    price = Item.objects.get(_id=item).price
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

                    return Response({"result": "success", "message": "Cart is updated successfully"},
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
                cart = Cart(
                    owner=user._id,
                    items=items_list,
                    quantity=quantity_list,
                    color=color_list,
                    measurement=measurement_list,
                    total_price=str(total_price),
                    created_at=today,
                    record_time=today
                )
                cart.save()
                # remove from wishlist
                if wishlist and item in wishlist.items:
                    wishlist.total_price = float(wishlist.total_price) - float(price)
                    wishlist.items.pop(wishlist.items.index(item))
                    wishlist.updated_at = today
                    wishlist.save()

                return Response({"result": "success", "message": "Your cart is create successfully"},
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

    # @permission_classes([IsAuthenticated, role_required("user")])
    @extend_schema(
        tags=["E-commerce Users"],
        request=AddToCartSerializer,
        responses={200: dict},
        description="E-commerce view set"
    )
    @action(detail=False, methods=['post'], url_path='add-to-wishlist')
    def add_wishlist(self, request):
        serializer = AddToWishListSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            item = serializer.validated_data["item"]

            # Value Validation
            validator = ToCartDataValidator(serializer.validated_data,
                                            fields=["item"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)

                selected_item = get_object_or_404(Item.objects, _id=item)
                wishlist = Wishlist.objects.filter(owner=user._id).first()

                if wishlist and (not item in wishlist.items):
                    price = Item.objects.get(_id=item).price
                    wishlist.items.append(item)
                    wishlist.total_price = float(wishlist.total_price) + float(price)
                    wishlist.record_time = today
                    wishlist.save()

                items_list = []
                total_price = 0.00
                price = Item.objects.get(_id=item).price
                total_price = float(total_price) + float(price)
                items_list.append(item)
                wishlist = Wishlist(
                    owner=user._id,
                    items=items_list,
                    total_price=str(total_price),
                )
                wishlist.save()

                return JsonResponse({"result": "success", "message": "Your wishlist is create successfully"},
                                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while carting: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while carting"},
                                status=status.HTTP_400_BAD_REQUEST)

    # @permission_classes([IsAuthenticated, role_required("user")])
    @extend_schema(
        tags=["E-commerce Users"],
        request=AddItemReviewSerializer,
        responses={200: dict},
        description="E-commerce view set"
    )
    @action(detail=False, methods=['post'], url_path='add-item-review')
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

                user_review = ItemReview.objects.filter(active_user=user.email).first()
                if user_review:
                    if rate != '':
                        user_review.rate = rate
                    if review != '':
                        user_review.review = review
                    user_review.record_time = today
                    user_review.save()

                    return JsonResponse({"result": "success", "message": "Item review is submitted successfully"}, status=status.HTTP_200_OK)

                review = ItemReview.objects.create(
                    active_user=user.email,
                    item=item,
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

    # @permission_classes([IsAuthenticated, role_required("user")])
    @extend_schema(
        tags=["E-commerce Users"],
        request=DeleteItemCartSerializer,
        responses={200: dict},
        description="E-commerce view set"
    )
    @action(detail=False, methods=['delete'], url_path='delete-item-cart')
    def delete_item_cart(self, request):
        serializer = DeleteItemCartSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            item = serializer.validated_data["item"]

            # Value Validation
            validator = ToCartDataValidator(serializer.validated_data,
                                            fields=["item"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)

                cart = get_object_or_404(Cart.objects, owner=user)

                if not item in cart.items:
                    raise ValueErrorException("Item is not found in your cart")

                cart_item = get_object_or_404(Item.objects, _id=item)

                if cart_item:
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

                return JsonResponse({"result": "success", "message": "Item is removed successfully"}, status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while deleting item from cart: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while deleting item from cart"},
                                status=status.HTTP_400_BAD_REQUEST)

class PaymentConfirmationViewSet(viewsets.ViewSet):
    """
    Payment confirmation view set
    """

    # @permission_classes([IsAuthenticated, role_required("user")])
    @extend_schema(
        tags=["Payment Confirmation Order"],
        request=PaymentConfirmationOrderEcommerceSerializer,
        responses={200: dict},
        description="Payment confirmation view set. Ecommerce payment confirmation is like checkout carted items"
    )
    @action(detail=False, methods=['post'], url_path='add-ecommerce-pc')
    def add_ecommerce_pc(self, request):
        serializer = PaymentConfirmationOrderEcommerceSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            name = serializer.validated_data["name"]
            email = serializer.validated_data["email"]
            phone = serializer.validated_data["phone"]
            method_ = serializer.validated_data["method"]
            proof = serializer.validated_data["proof"]

            # Value Validation
            validator = EcommercePCValidator(serializer.validated_data,
                                            fields=["name", "email", "phone", "method", "proof"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)

                if user.email != email.lower():
                    raise ValueErrorException("Failed to request payment confirmation approval")

                selected_method = get_object_or_404(PaymentMethod.objects, _id=method_)
                cart = get_object_or_404(Cart.objects, owner=user.email)

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
                    user_name=name,
                    user_email=email.lower(),
                    user_phone=phone,
                    items=cart.items,
                    quantity=cart.quantity,
                    total_price=cart.total_price,
                    proof=file_name,
                    method_id=method_,
                    created_at=today,
                    updated_at=today
                )
                pc.save()

                return JsonResponse({"result": "success", "message": "Payment confirmation is added successfully"},
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

    # @permission_classes([IsAuthenticated, role_required("user")])
    @extend_schema(
        tags=["Payment Confirmation Order"],
        request=PackagePCSerializer,
        responses={200: dict},
        description="Payment confirmation view set"
    )
    @action(detail=False, methods=['post'], url_path='add-package-pc')
    def add_package_pc(self, request):
        serializer = PaymentConfirmationOrderEcommerceSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            fname = serializer.validated_data["fname"]
            lname = serializer.validated_data["lname"]
            email = serializer.validated_data["email"]
            phone = serializer.validated_data["phone"]
            plan = serializer.validated_data["plan"]
            method_ = serializer.validated_data["method"]
            proof = serializer.validated_data["proof"]

            # Value Validation
            validator = PackagePCValidator(serializer.validated_data,
                                            fields=["fname", "lname", "email", "phone", "plan", "method", "proof"], null_validation=True)
            if not validator.is_valid():
                raise ValidationException(validator.errors)

            with transaction.atomic():
                # Data Validation
                user = get_object_or_404(CustomUser.objects, email=request.user)

                if user.email != email.lower():
                    raise ValueErrorException("Use your account email to process subscription")

                package_plan = get_object_or_404(Package.objects, _id=plan)
                payment_method = get_object_or_404(PaymentMethod.objects, _id=method_)

                if PackagePC.objects.filter(Q(user_id=user._id) & Q(status='approved')).exists():
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
                    package_id=str(package_plan._id),
                    user_id=str(user._id),
                    price=package_plan.price,
                    proof=file_name,
                    method_id=method_,
                    created_at=today,
                    updated_at=today
                )
                pc.save()

                return JsonResponse({"result": "success", "message": "Subscription payment confirmation is added successfully"},
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

    # @permission_classes([IsAuthenticated, role_required("user")])
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

    # @permission_classes([IsAuthenticated, role_required("user")])
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

            response = {
                "courses": []
            }

            for course in courses_list.data:
                temp_data = []

                category = CourseCategory.objects.filter(_id=course.get('category')).first()
                category_name = capwords(category.name) if category else "UNCATEGORIZED"
                temp_data.append(capwords(category_name))

                temp_data.append(course)

                response["courses"].append(temp_data)

            return JsonResponse({"result": "success", "message": "Courses list", "content": response},
                                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Courses is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching courses: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching courses."},
                                status=status.HTTP_400_BAD_REQUEST)

    # @permission_classes([IsAuthenticated, role_required("user")])
    @extend_schema(
        tags=["Course Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-course/(?P<_id>[^/.]+)')
    def get_course(self, request, _id=None):
        try:
            get_course = get_object_or_404(Course.objects, _id=_id)

            lessons = CourseLesson.objects.filter(course=get_course._id)
            if not lessons:
                raise Http404

            # response structure course info + lessons + meal plans
            response = {
                "isSubscribed": "false",
                "category": {},
                "course": {},
                "lessons": [],
                "meal_plans": [],
            }

            # check if the logged user is subscribed to package
            logged_user = CustomUser.objects.filter(email=request.use).first()
            user = CustomUsers.objects.filter(user=logged_user).first()

            if "course" in user["package"]:
                response["isSubscribed"] = "true"

            # Get course category
            category = get_object_or_404(CourseCategory.objects, _id=get_course.catgeory)
            response["category"] = {
                "name": capwords(category.name),
                "color": category.color,
                "icon": category.icon
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
            meal_plans = MealPlan.objects.filter(course=get_course._id)
            for meal_plan in meal_plans:
                temp_data = {
                    "_id": meal_plan._id,
                    "name": capwords(meal_plans.name),
                    "overview": capwords(meal_plans.overview),
                    "course": meal_plan.course,
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
    Meal plans view set
    """

    # @permission_classes([IsAuthenticated, role_required("user")])
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

            response = {
                "meal_plans": []
            }

            for meal_plan in meal_plans_list.data:
                temp_data = []

                course = Course.objects.filter(_id=meal_plan.course).first()
                course_name = capwords(course.title) if course else "UNCATEGORIZED"
                temp_data.append(capwords(course_name))

                temp_data.append(meal_plan)

                response["meal_plans"].append(temp_data)

            return JsonResponse(
                {"result": "success", "message": "Meal plans list", "content": response},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Meal plans is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching meal plans: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching meal plans."},
                                status=status.HTTP_400_BAD_REQUEST)

    # @permission_classes([IsAuthenticated, role_required("user")])
    @extend_schema(
        tags=["Meal Plan Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-meal-plan/(?P<_id>[^/.]+)')
    def get_meal_plan(self, request, _id=None):
        try:
            get_meal_plan = get_object_or_404(MealPlan.objects, _id=_id)

            recipes = MealPlanRecipe.objects.filter(meal=get_meal_plan._id)
            if not recipes:
                raise Http404

            # response structure course info + lessons + meal plans
            response = {
                "isSubscribed": "false",
                "meal_plans": {},
                "recipes": [],
            }

            # check if the logged user is subscribed to package
            logged_user = CustomUser.objects.filter(email=request.use).first()
            user = CustomUsers.objects.filter(user=logged_user).first()

            if "meal plan" in user["package"]:
                response["isSubscribed"] = "true"

            # Get the course of meal plan
            course = Course.objects.filter(_id=get_meal_plan.course)
            course_name = ""
            if course:
                course_name = course.get("title")

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

    # @permission_classes([IsAuthenticated, role_required("user")])
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

    # @permission_classes([IsAuthenticated, role_required("user")])
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

            response = {
                "audiobooks": [],
            }

            for audio_book in audio_books_list.data:
                temp_data = []

                category = AudiobookCategory.objects.filter(_id=audio_book.get('category')).first()
                category_name = capwords(category.name) if category else "UNCATEGORIZED"
                temp_data.append(capwords(category_name))

                temp_data.append(audio_book)

                response["audiobooks"].append(temp_data)

            return JsonResponse(
                {"result": "success", "message": "Audiobooks list", "content": response},
                status=status.HTTP_200_OK)

        except Http404:
            return JsonResponse({"result": "error", "message": "Audiobooks is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while fetching audiobooks: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while fetching audiobooks."},
                                status=status.HTTP_400_BAD_REQUEST)

    # @permission_classes([IsAuthenticated, role_required("user")])
    @extend_schema(
        tags=["Audiobook Users"],
        responses={200: dict},
        description=""
    )
    @action(detail=False, methods=['get'], url_path='get-audio-book/(?P<_id>[^/.]+)')
    def get_audio_book(self, request, _id=None):
        try:
            get_audio_book = get_object_or_404(Audiobook.objects, _id=_id)

            # response structure course info + lessons + meal plans
            response = {
                "isSubscribed": "false",
                "audio_book": {}
            }

            # check if the logged user is subscribed to package
            logged_user = CustomUser.objects.filter(email=request.use).first()
            user = CustomUsers.objects.filter(user=logged_user).first()

            if "audio book" in user["package"]:
                response["isSubscribed"] = "true"

            audio_book_category = AudiobookCategory.objects.filter(_id=get_audio_book.category)
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
