from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from admins.serializers import *

class Pagination(PageNumberPagination):
    # /api/grn?page=2&page_size=20
    page_size = 10  # Number of items per page
    page_size_query_param = 'page_size'
    max_page_size = 100

class PaginationLimitOffset(LimitOffsetPagination):
    #/api/grn?limit=10&offset=10 → Next 10 results (skip first 10)
    default_limit = 10  # Default items per request
    max_limit = 100  # Maximum items a user can request

class CourseDataPagination(Pagination):
    
    def paginate_course_categories(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = CourseCategorySerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)
    
    def paginate_courses(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = CourseSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class CourseLessonDataPagination(Pagination):

    def paginate_course_lessons(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = CourseLessonSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class CourseReviewDataPagination(Pagination):

    def paginate_course_reviews(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = CourseReviewSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class MealPlanDataPagination(Pagination):

    def paginate_meal_plan(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = MealPlanSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class MealPlanRecipeDataPagination(Pagination):

    def paginate_meal_recipe(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = MealPlanRecipeSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class AudiobookCategoryDataPagination(Pagination):

    def paginate_audiobook_category(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = AudiobookCategorySerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class AudiobookDataPagination(Pagination):

    def paginate_audiobook(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = AudiobookSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class ItemCategoryDataPagination(Pagination):

    def paginate_category(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = ItemCategorySerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class ItemDataPagination(Pagination):

    def paginate_item(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = ItemSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class ItemCartDataPagination(Pagination):

    def paginate_cart(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = ItemCartSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class ItemWishlistDataPagination(Pagination):

    def paginate_wishlist(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = ItemWishlistSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class PaymentMethodDataPagination(Pagination):

    def paginate_payment_method(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = PaymentMethodSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class PackagePlanDataPagination(Pagination):

    def paginate_package(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = PackagePlanSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class EcommercePCDataPagination(Pagination):

    def paginate_pc(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = EcommercePCSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class PackagePCDataPagination(Pagination):

    def paginate_pc(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = PackagePCSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class AppointmentDataPagination(Pagination):

    def paginate_appointment(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = AppointmentSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

class LocalizationDataPagination(Pagination):

    def paginate_localization(self, request, queryset):
        paginated_queryset = self.paginate_queryset(queryset, request)
        serializer = LocalizationSerializer(paginated_queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)