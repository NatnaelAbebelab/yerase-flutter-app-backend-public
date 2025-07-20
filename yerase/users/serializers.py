from rest_framework import serializers
from .models import *

class CustomerAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'  # Include all fields