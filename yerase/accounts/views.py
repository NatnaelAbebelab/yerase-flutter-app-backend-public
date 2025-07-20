from django.http import JsonResponse
from admins.startup import create_default_users, create_default_course_category
from rest_framework.views import APIView, status
import logging

logger = logging.getLogger(__name__)

class CreateDefaultUserView(APIView):
    def post(self, request):
        try:
            create_default_users()
            create_default_course_category()
            logger.info("Default user created or already exists.")
            return JsonResponse({"result": "user created"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error creating default user: {e}")
            return JsonResponse({"result": "user is not created"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)