from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView, TokenVerifyView
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import *

router = DefaultRouter()
router.register(r'account', CustomerAccountViewSet, basename='account')
router.register(r'appointment', AppointmentViewSet, basename='appointment')
router.register(r'shop', EcommerceViewSet, basename='shop')
router.register(r'payment-confirmation', PaymentConfirmationViewSet, basename='payment-confirmation')
router.register(r'courses', CourseViewSet, basename='courses')
router.register(r'meal-plans', MealPlanViewSet, basename='meal-plans')
router.register(r'audiobook', AudioBookViewSet, basename='audiobook')
router.register(r'package', PackagePlanViewSet, basename='package')
#urlpatterns = router.urls


urlpatterns = [
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('api/token/verify/', TokenVerifyView.as_view(), name="token_verify"),

    # path('signup/', RegisterView.as_view(), name='signup'),
    # path('activate/', ActivateAccountView.as_view(), name='activate'),
    # path('signin/', SignInView.as_view(), name='signin'),
    # path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    # path('update-profile/', UpdateProfileView.as_view(), name='update-profile'),
    # path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    #
    # path('request-appointment/', BookAppointmentView.as_view(), name='request-appointment'),
] + router.urls