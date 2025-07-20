from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError
from django.db import connection
import sys, logging

logger = logging.getLogger(__name__)
class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admins'
    
    def ready(self):
        """
        This method is called when Django starts up.
        It attempts to create default users by directly calling the function.
        """
       
        if connection.is_usable():
            is_migrating = 'makemigrations' in sys.argv or 'migrate' in sys.argv

            if not is_migrating:
                try:
                    # Import the function directly
                    from .startup import create_default_users, create_default_course_category
                    create_default_users()
                    create_default_course_category()
                    logger.info("Default users creation attempted via AppConfig.ready().")
                    
                    
                except (OperationalError, ProgrammingError) as e:
                    # Catch specific database errors if tables aren't ready
                    logger.warning(f"Database not ready or schema mismatch during AppConfig.ready() default user creation: {e}")
                except Exception as e:
                    logger.error(f"Error during AppConfig.ready() default user creation: {e}")
            else:
                logger.info("Skipping default user creation in AppConfig.ready() during migration/makemigrations command.")
        else:
            logger.warning("Database connection not usable during AppConfig.ready(). Skipping default user creation.")