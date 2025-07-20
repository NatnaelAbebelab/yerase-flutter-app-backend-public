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
from django.db.models import Q, F
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.template.loader import get_template
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from pydub import AudioSegment
from rest_framework.decorators import permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

from utils.exceptions import *
from utils.permissions import role_required
from .reponseSerializers import GenericSuccessResponseSerializer
from .requestSerializers import *
from .services.pagination import *
from .services.roles import get_user_role
from .services.validations import *
from .utility.token import get_tokens_for_user

from admins.models import *

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

class RegisterView(APIView):
    """
    Register class based view to register users
    """

    @extend_schema(
        tags=["Customer Account"],
        request=CreateAccountSerializer,
        responses={200: dict}
    )
    def post(self, request):
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
                while 1:
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
                    password=make_password(password),
                    weight=weight,
                    height=height,
                    age=age,
                    gender=gender,
                    otp_code=otp_code,
                    created_at=today,
                    update_at=today,
                )
                customer.save()

                # send email notification / OTP
                # send email to user email
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
                email.content_subtype = 'html'  # Specify that the email content is HTML
                email.send()

                return JsonResponse(
                    {"result": "success", "message": "You have signed up successfully."},
                    status=status.HTTP_200_OK)

        except (BaseClassSerializerException, ValidationException, ValueDuplicationException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while creating customer: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while creating customer"},
                                status=status.HTTP_400_BAD_REQUEST)

class ActivateAccountView(APIView):
    """
    Activate account class based view.
    Users activate their account by login/signin in which the sign in URL contains the OTP code
    """

    @extend_schema(
        tags=["Customer Account"],
        request=AccountActivationSerializer,
        responses={200: dict}
    )
    def post(self, request):
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
                        return JsonResponse({"result": "success", "message": "You have activates your account successfully."}, status=status.HTTP_200_OK)
                return JsonResponse({"result": "error", "message": "Your account is not found"}, status=status.HTTP_404_NOT_FOUND)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while activating account: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while activating account"},
                                status=status.HTTP_400_BAD_REQUEST)

class SignInView(APIView):
    """
    Class based view to sign in view
    """

    @extend_schema(
        tags=["Customer Account"],
        request=SignInSerializer,
        responses={200: dict}
    )
    def post(self, request):
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
                    return JsonResponse({"result": "success", "message": "You have signed in successfully"}, status=status.HTTP_200_OK)
                return JsonResponse({"result": "error", "message": "Your account is not found"}, status=status.HTTP_404_NOT_FOUND)

        except (BaseClassSerializerException, ValidationException, ValueErrorException) as e:
            return JsonResponse({"result": "error", "message": e.message}, status=e.code)
        except Http404:
            return JsonResponse({"result": "error", "message": "Record is not found."},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Error occurred while signing in: %s", e)
            return JsonResponse({"result": "error", "message": "Error occurred while signing in"},
                                status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordView(APIView):
    """
    Class based view to reset password
    When the user forgot password they can reset the password
    """

    @extend_schema(
        tags=["Customer Account"],
        request=ResetPasswordSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)

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

@permission_classes([IsAuthenticated, role_required(["user"])])
class UpdateProfileView(APIView):
    """
    Update account profile
    """

    @extend_schema(
        tags=["Customer Account"],
        request=UpdateAccountProfileSerializer,
        responses={200: dict}
    )
    def post(self, request):
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

@permission_classes([IsAuthenticated, role_required(["user"])])
class ChangePasswordView(APIView):
    """
    Change password class based view
    Users change password on their account settings
    """

    @extend_schema(
        tags=["Customer Account"],
        request=ChangePasswordSerializer,
        responses={200: dict}
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)

        try:
            if not serializer.is_valid():
                raise BaseClassSerializerException(serializer.errors)

            current = serializer.validated_data["current"] # current password of logged user
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

@permission_classes([IsAuthenticated, role_required(["users"])])
class BookAppointmentView(APIView):
    """
    Appointment class based view
    """

    @extend_schema(
        tags=["Customer Appointment"],
        request=BookAppointmentSerializer,
        responses={200: dict}
    )
    def post(self, request):
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

@permission_classes([IsAuthenticated, role_required(["users"])])
class EcommerceViewSet(viewsets.ViewSet):
    """
    E-commerce class based view
    """

    @action(detail=False, methods=['post'], url_path='add-cart')
    @extend_schema(
        request=AddToCartSerializer,
        responses={200: GenericSuccessResponseSerializer},
        summary="Add Item to Cart",
        description="Adds a new item to the user's cart..."
    )
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

                cart = Cart.objects.filter(owner=user._id).first();
                wishlist = Wishlist.objects.filter(owner=user._id).first()

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

                    return Response({"result": "success", "message": "Cart is updated successfully"}, status=status.HTTP_200_OK)

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

    @action(detail=False, methods=['post'], url_path='add-wishlist')
    @extend_schema(
        tags=["E-commerce Cart"],
        request=AddToWishListSerializer,
        responses={200: dict}
    )
    def add_to_wishlist(self, request):
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



























