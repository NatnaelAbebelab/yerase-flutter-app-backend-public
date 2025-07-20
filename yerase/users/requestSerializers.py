# serializers.py
from rest_framework import serializers

"""
==============> Customer Account Serializer <=============
"""
class CreateAccountSerializer(serializers.Serializer):
    fname = serializers.CharField(required=True)
    lname = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    # Default to 0 if not provided
    weight = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)
    height = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=0)
    age = serializers.IntegerField(required=False, default=0)

    # Default to '-' if not provided
    gender = serializers.CharField(required=False, default='-')

class AccountActivationSerializer(serializers.Serializer):
    otp_code = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)

class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)

class ResetUserPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class UpdateAccountProfileSerializer(serializers.Serializer):
    fname = serializers.CharField(required=False, allow_blank=True)
    lname = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    weight = serializers.DecimalField(required=False, default=0, max_digits=3, decimal_places=2)
    height = serializers.DecimalField(required=False, default=0, max_digits=3, decimal_places=2)
    age = serializers.IntegerField(required=False, default=0)
    gender = serializers.CharField(required=False, allow_blank=True)
    profile = serializers.FileField(required=False,allow_null=True)

class ChangePasswordSerializer(serializers.Serializer):
    current = serializers.CharField(required=True)
    new_pass = serializers.CharField(required=True)

class BookAppointmentSerializer(serializers.Serializer):
    subject = serializers.CharField(required=True)
    message = serializers.CharField(required=True)
    schedule = serializers.DateField(required=True)

class AddToCartSerializer(serializers.Serializer):
    item = serializers.CharField(required=True)
    quantity = serializers.IntegerField(required=True)
    color = serializers.CharField(required=True)
    measurement = serializers.CharField(required=True)

class AddToWishListSerializer(serializers.Serializer):
    item = serializers.CharField(required=True)

class AddItemReviewSerializer(serializers.Serializer):
    item = serializers.CharField(required=True)
    rate = serializers.DecimalField(required=True, max_digits=2, decimal_places=2)
    review = serializers.CharField(required=True)

class DeleteItemCartSerializer(serializers.Serializer):
    item = serializers.CharField(required=True)

class PaymentConfirmationOrderEcommerceSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True)
    method_ = serializers.CharField(required=True)
    proof = serializers.FileField(required=True)

class PackagePCSerializer(serializers.Serializer):
    fname = serializers.CharField(required=True)
    lname = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True)
    plan = serializers.CharField(required=True)
    method_ = serializers.CharField(required=True)
    proof = serializers.FileField(required=True)
