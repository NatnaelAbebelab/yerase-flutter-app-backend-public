from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView, TokenVerifyView
from django.urls import path
from .views import *

urlpatterns = [
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('api/token/verify/', TokenVerifyView.as_view(), name="token_verify"),
    
    path('account/', AdminAccountView.as_view(), name='account'),
    path('login/', AdminLoginView.as_view(), name='login'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('update-profile/', AdminUpdateProfileView.as_view(), name='update-profile'),
    path('change-password/', AdminChangePasswordView.as_view(), name='change-password'),
    path('recover-password/', AdminRecoverPasswordView.as_view(), name='recover-password'),
    path('logout/', AdminLogoutView.as_view(), name='logout'),
    
    path('course-category/', CourseCategoryView.as_view(), name='course-category'),
    path('course/', CourseView.as_view(), name='course'),
    path('course-lesson/', CourseLessonView.as_view(), name='course-lesson'),
    path('course-review/', CourseReviewView.as_view(), name='course-review'),
    path('item-cart/', ItemCartView.as_view(), name='item-cart'),
    path('item-wishlist/', ItemWishlistView.as_view(), name='item-wishlist'),

    path('meal-plans/', MealPlanView.as_view(), name='meal-plans'),
    path('meal-plan-recipe/', MealPlanRecipeView.as_view(), name='meal-plan-recipe'),

    path('audiobook-category/', AudiobookCategoryView.as_view(), name='audiobook-category'),
    path('audiobook/', AudiobookView.as_view(), name='audiobook'),

    path('item-category/', ItemCategoryView.as_view(), name='item-category'),
    path('item/', ItemView.as_view(), name='item'),

    path('payment-method/', PaymentMethodView.as_view(), name='payment-method'),

    path('package-plan/', PackagePlanView.as_view(), name='package-plan'),

    path('ecommercePC/', EcommercePCView.as_view(), name='ecommerce-pc'),

    path('packagePC/', PackagePCView.as_view(), name='package-pc'),

    path('appointment/', AppointmentView.as_view(), name='appointment'),

    path('localization/', LocalizationView.as_view(), name='localization')
]