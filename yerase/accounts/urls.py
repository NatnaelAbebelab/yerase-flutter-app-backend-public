from django.urls import path
from .views import *

urlpatterns = [
    path('add-user/', CreateDefaultUserView.as_view(), name='add-user'),
]