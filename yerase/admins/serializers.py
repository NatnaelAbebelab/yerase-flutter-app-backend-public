from rest_framework import serializers
from .models import *

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role']
        read_only_fields = ['id', 'username']

class UserAdminSerializer(serializers.ModelSerializer):
    admin = CustomUserSerializer(read_only=True)

    class Meta:
        model = CustomAdmin
        # Include all CustomAdmin fields plus nested user info (admin)
        fields = [
            '_id', 'admin', 'phone', 'otp_code', 'profile', 'is_deleted',
            'created_by', 'created_at', 'updated_by', 'updated_at', 'record_time'
        ]

class CourseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseCategory
        fields = '__all__'  # Include all fields

class CourseSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    category_color = serializers.SerializerMethodField()
    category_icon = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [f.name for f in Course._meta.fields] + ["category_name", "category_color", "category_icon"]
        
    def get_category_name(self, obj):
        # Corrected: Accessing .name and checking obj.category
        return obj.category.name if obj.category else None

    def get_category_color(self, obj):
        # Assuming CourseCategory has a 'color' field
        return obj.category.color if obj.category else None

    def get_category_icon(self, obj):
        # Assuming CourseCategory has an 'icon' field
        return obj.category.icon if obj.category else None

class CourseLessonSerializer(serializers.ModelSerializer):
    course_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseLesson
        fields = [f.name for f in CourseLesson._meta.fields] + ["course_name"]

    def get_course_name(self, obj):
        return obj.course.title if obj.course else None

class CourseReviewSerializer(serializers.ModelSerializer):
    course_name = serializers.SerializerMethodField()

    class Meta:
        model = CourseReview
        fields = [f.name for f in CourseReview._meta.fields] + ["course_name"]

    def get_course_name(self, obj):
        return obj.course.title if obj.course else None

class MealPlanSerializer(serializers.ModelSerializer):
    course_name = serializers.SerializerMethodField()

    class Meta:
        model = MealPlan
        fields = [f.name for f in MealPlan._meta.fields] + ["course_name"]

    def get_course_name(self, obj):
        return obj.course.title if obj.course else None

class MealPlanRecipeSerializer(serializers.ModelSerializer):
    meal = serializers.SerializerMethodField()

    class Meta:
        model = MealPlanRecipe
        fields = [f.name for f in MealPlanRecipe._meta.fields] + ["meal"]

    def get_meal(self, obj):
        return obj.meal.name if obj.meal else None

class AudiobookCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AudiobookCategory
        fields = '__all__'

class AudiobookSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()

    class Meta:
        model = Audiobook
        fields = [f.name for f in Audiobook._meta.fields] + ["category"]

    def get_category(self, obj):
        category = obj.category
        if category:
            # Return a dictionary of relevant fields
            return {
                "id": category._id,
                "name": category.name,
            }
        return None


class ItemCategorySerializer(serializers.ModelSerializer):
    measurement_name = serializers.SerializerMethodField()

    class Meta:
        model = ItemCategory
        fields = '__all__'  # Includes all fields from the model plus measurement_name

    def get_measurement_name(self, obj):
        units = {
            'f': 'Free',
            's': 'Size',
            'kg': 'Kilograms',
            'l': 'Litter'
        }
        return units.get(obj.measurement, obj.measurement)

class ItemSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = [f.name for f in Item._meta.fields] + ["category"]

    def get_category(self, obj):
        return obj.category.name if obj.category else "UNCATEGORIZED"

class ItemCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = '__all__'

class ItemWishlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = '__all__'

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'

class PackagePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = '__all__'

class ItemLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ["_id", "name", "price"]

class EcommercePCSerializer(serializers.ModelSerializer):
    method = serializers.SerializerMethodField()
    items_detail = serializers.SerializerMethodField()

    class Meta:
        model = EcommercePC
        exclude = ["items"]

    def get_method(self, obj):
        return obj.method.name if obj.method else None

    def get_items_detail(self, obj):
        if not obj.items:
            return []
        items = Item.objects.filter(_id__in=obj.items)
        return ItemLightSerializer(items, many=True).data

class PackagePCSerializer(serializers.ModelSerializer):
    package = PackagePlanSerializer(read_only=True)
    method = serializers.SerializerMethodField()

    class Meta:
        model = PackagePC
        fields = [f.name for f in PackagePC._meta.fields] + ["method"]

    def get_method(self, obj):
        return obj.method.name if obj.method else None

class AppointmentSerializer(serializers.ModelSerializer):
    """
    There is customer linked with appointment
    """
    customer = CustomUserSerializer(read_only=True)
    class Meta:
        model = Appointment
        fields = '__all__'

class LocalizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Localization
        fields = '__all__'