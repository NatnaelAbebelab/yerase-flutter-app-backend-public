# serializers.py
from collections.abc import set_iterator
from operator import truediv

from rest_framework import serializers
from accounts.enums import Roles  # Use your actual import path

"""
==============> Account Serializer <=============
"""
class AdminLoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True)
    
class AdminAccountCreateSerializer(serializers.Serializer):
    fname = serializers.CharField(required=True)
    lname = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    role = serializers.CharField(required=True)

class AdminAccountPatchSerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    fname = serializers.CharField(required=False, allow_blank=True)
    lname = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField(required=False, allow_blank=True)

class ResetPasswordSerializer(serializers.Serializer):
    otp_code = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

class AdminUpdateProfileInfoSerializer(serializers.Serializer):
    profile = serializers.ImageField(required=False, allow_null=True)
    fname = serializers.CharField(required=False, allow_blank=True)
    lname = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)

class AdminChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    
class AdminRecoverPasswordSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    
"""
==============> Courses Serializer <=============
"""
class AddCourseCategorySerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    color = serializers.CharField(required=True)
    icon = serializers.ImageField(required=True)

class UpdateCourseCategorySerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    color = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    icon = serializers.ImageField(required=False, allow_null=True)

class AddCourseSerializer(serializers.Serializer):
    title = serializers.CharField(required=True)
    category = serializers.CharField(required=True)
    thumbnail = serializers.ImageField(required=True)
    overview = serializers.CharField(required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    objectives =  serializers.ListField(required=False, allow_empty=True, allow_null=True)
    intro = serializers.CharField(required=True)
    level = serializers.CharField(required=True)
    certificate = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(required=True)

class UpdateCourseSerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    title = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    thumbnail = serializers.ImageField(required=False, allow_null=True)
    overview = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    objectives = serializers.ListField(required=False, allow_empty=True, allow_null=True)
    intro = serializers.CharField(required=False, allow_blank=True)
    level = serializers.CharField(required=False, allow_blank=True)
    certificate = serializers.CharField(required=False, allow_blank=True)
    language = serializers.CharField(required=False, allow_blank=True)

class AddCourseLessonSerializer(serializers.Serializer):
    title = serializers.CharField(required=True)
    course = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    thumbnail = serializers.ImageField(required=True)
    video_id = serializers.CharField(required=True)

class UpdateCourseLessonSerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    title = serializers.CharField(required=False, allow_blank=True)
    course = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    thumbnail = serializers.ImageField(required=False, allow_null=True)
    video_id = serializers.CharField(required=False, allow_blank=True)

class AddCourseReviewSerializer(serializers.Serializer):
    user = serializers.CharField(required=True)
    course = serializers.CharField(required=True)
    rate = serializers.CharField(required=True)
    review = serializers.CharField(required=True)

class UpdateCourseReviewSerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    user = serializers.CharField(required=False, allow_blank=True)
    course = serializers.CharField(required=False, allow_blank=True)
    rate = serializers.CharField(required=False, allow_blank=True)
    review = serializers.CharField(required=False, allow_blank=True)

class AddMealPlanSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    overview = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    thumbnail = serializers.ImageField(required=True)
    course = serializers.CharField(required=True)
    intro = serializers.CharField(required=True)

class UpdateMealPlanSerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    overview = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    thumbnail = serializers.ImageField(required=False, allow_null=True)
    course = serializers.CharField(required=False, allow_blank=True)
    intro = serializers.CharField(required=False, allow_blank=True)

class AddMealPlanRecipeSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    plan = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    thumbnail = serializers.ImageField(required=True)
    video = serializers.CharField(required=True)

class UpdateMealPlanRecipeSerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    plan = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    thumbnail = serializers.ImageField(required=False, allow_null=True)
    video = serializers.CharField(required=False, allow_blank=True)

class AddAudiobookCategorySerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    color = serializers.CharField(required=True)
    icon = serializers.ImageField(required=True)

class UpdateAudiobookCategorySerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    color = serializers.CharField(required=False, allow_blank=True)
    icon = serializers.ImageField(required=False, allow_null=True)

class AddAudiobookSerializer(serializers.Serializer):
    title = serializers.CharField(required=True)
    overview = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    thumbnail = serializers.ImageField(required=True)
    category = serializers.CharField(required=True)
    audio = serializers.FileField(required=True)

class UpdateAudiobookSerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    title = serializers.CharField(required=False, allow_blank=True)
    overview = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    thumbnail = serializers.ImageField(required=False, allow_null=True)
    category = serializers.CharField(required=False, allow_blank=True)
    audio = serializers.FileField(required=False, allow_null=True)

class AddItemCategorySerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    measurement = serializers.CharField(required=True)
    color = serializers.CharField(required=True)
    icon = serializers.ImageField(required=True)

class UpdateItemCategorySerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    measurement = serializers.CharField(required=False, allow_blank=True)
    color = serializers.CharField(required=False, allow_blank=True)
    icon = serializers.ImageField(required=False, allow_null=True)

class AddItemSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    overview = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    thumbnail = serializers.ImageField(required=True)
    category = serializers.CharField(required=True)
    min_value = serializers.CharField(required=True)
    max_value = serializers.CharField(required=True)
    sizes = serializers.ListField(required=True)
    price = serializers.CharField(required=True)
    quantity = serializers.CharField(required=True)
    variation_img = serializers.ListField(required=True)
    variation_color = serializers.ListField(required=True)
    variation_qty = serializers.ListField(required=True)

class UpdateItemSerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    overview = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    thumbnail = serializers.ImageField(required=False, allow_null=True)
    category = serializers.CharField(required=False, allow_blank=True)
    min_value = serializers.CharField(required=False, allow_blank=True)
    max_value = serializers.CharField(required=False, allow_blank=True)
    sizes = serializers.ListField(required=False, allow_empty=True)
    price = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.CharField(required=False, allow_blank=True)
    variation_img = serializers.ListField(required=False, allow_empty=True)
    variation_color = serializers.ListField(required=False, allow_empty=True)
    variation_qty = serializers.ListField(required=False, allow_empty=True)

class AddPaymentMethodSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    icon = serializers.ImageField(required=True)
    holder = serializers.CharField(required=True)
    num = serializers.CharField(required=True)

class UpdatePaymentMethodSerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    icon = serializers.ImageField(required=False, allow_null=True)
    holder = serializers.CharField(required=False, allow_blank=True)
    num = serializers.CharField(required=False, allow_blank=True)

class AddPackagePlanSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    overview = serializers.CharField(required=True)
    price = serializers.CharField(required=True)
    entities = serializers.ListField(required=True)
    offers = serializers.ListField(required=True)

class UpdatePackagePlanSerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    overview = serializers.CharField(required=False, allow_blank=True)
    price = serializers.CharField(required=False, allow_blank=True)
    entities = serializers.ListField(required=False, allow_empty=True)
    offers = serializers.ListField(required=False, allow_empty=True)

class AddEcommercePCSerializer(serializers.Serializer):
    order_id = serializers.CharField(required=True)
    user_name = serializers.CharField(required=True)
    user_email = serializers.CharField(required=True)
    user_phone = serializers.CharField(required=True)
    items = serializers.ListField(required=True)
    price = serializers.CharField(required=True)
    method_id = serializers.CharField(required=True)
    proof = serializers.FileField(required=True)

class UpdateEcommercePCSerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    status = serializers.CharField(required=True)

class AddPackagePCSerializer(serializers.Serializer):
    package = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    method_id = serializers.CharField(required=True)
    proof = serializers.FileField(required=True)

class UpdatePackagePCSerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    status = serializers.CharField(required=True)

class AddAppointmentSerializer(serializers.Serializer):
    customer = serializers.CharField(required=True)
    subject = serializers.CharField(required=True)
    message = serializers.CharField(required=True)
    schedule = serializers.CharField(required=True)

class UpdateAppointmentSerializer(serializers.Serializer):
    _id = serializers.CharField(required=True)
    link = serializers.CharField(required=False, allow_blank=True)
    _status = serializers.CharField(required=False, allow_blank=True)

class AddLocalizationSerializer(serializers.Serializer):
    content_key = serializers.CharField(required=True)
    content_value = serializers.CharField(required=True)
    entity = serializers.CharField(required=True)

class UpdateLocalizationSerializer(serializers.Serializer):
    format_id = serializers.CharField(required=True)
    content_key = serializers.CharField(required=False, allow_blank=True)
    content_value = serializers.CharField(required=False, allow_blank=True)
    entity = serializers.CharField(required=False, allow_blank=True)