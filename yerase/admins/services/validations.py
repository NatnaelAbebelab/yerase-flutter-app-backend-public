import re
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from accounts.models import CustomUser
from accounts.enums import Roles

class AdminAccountDataValidator:
    def __init__(self, data, fields=None, exclude_user_id=None, empty_validation=None, null_validation=None):
        self.data = data
        self.fields = fields or ["fname", "lname", "email", "phone", "role", "password"]
        self.exclude_user_id = exclude_user_id
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "fname" in self.fields:
            self.validate_fname()
        if "lname" in self.fields:
            self.validate_lname()
        if "email" in self.fields:
            self.validate_email()
        if "phone" in self.fields:
            self.validate_phone()
        if "role" in self.fields:
            self.validate_role()
        if "password" in self.fields:
            self.validate_password()
        return not bool(self.errors)

    def validate_fname(self):
        fname = self.data.get("fname")
        
        if self.empty_validation and not fname:
            self.errors["fname"] = "First name is required."
            return
        if self.null_validation and not fname:
            self.errors["fname"] = "First name is required."
            return
        if self.empty_validation and not re.match(r'^[a-zA-Z\s]+$', fname):
            self.errors["fname"] = "Name must contain only letters and spaces."
            return

    def validate_lname(self):
        lname = self.data.get("lname", "")
        
        if self.empty_validation and not lname:
            self.errors["lname"] = "Last name is required."
            return
        if self.null_validation and not lname:
            self.errors["lname"] = "Last name is required."
            return
        if self.empty_validation and not re.match(r'^[a-zA-Z\s]+$', lname):
            self.errors["lname"] = "Name must contain only letters and spaces."
            return

    def validate_email(self):
        email = self.data.get("email", "")

        if self.empty_validation and not email:
            self.errors["email"] = "Email is required."
            return
        if self.null_validation and not email:
            self.errors["email"] = "Email is required."
            return
        try:
            if self.empty_validation:
                validate_email(email)
        except ValidationError:
            self.errors["email"] = "Invalid email address."
            return
        return

    def validate_phone(self):
        phone = self.data.get("phone", "")
        
        if self.empty_validation and not phone:
            self.errors["phone"] = "Phone is required."
            return
        if self.null_validation and not phone:
            self.errors["phone"] = "Phone is required."
            return
        if self.empty_validation and not re.match(r'^\+?1?\d{9,15}$', phone):
            self.errors["phone"] = "Invalid phone number."
            return
    
    def validate_role(self):
        role = self.data.get("role", "")
        if self.empty_validation and not role:
            self.errors["role"] = "Role is required."
            return
        if self.null_validation and not role:
            self.errors["role"] = "Role is required."
            return
        if role not in Roles.values:
            self.errors["role"] = f"Invalid role. Must be one of: {', '.join(Roles.values)}"
            return
        
    def validate_password(self):
        password = self.data.get("password")
        
        if self.empty_validation and not password:
            self.errors["password"] = "Phone is required."
            return
        if self.null_validation and not password:
            self.errors["password"] = "Phone is required."
            return
        if self.empty_validation and len(password) < 8:
            self.errors["password"] = "Password must be at least 8 characters long."
            return
        elif not re.search(r'[a-z]', password):
            self.errors["password"] = "Password must contain at least one lowercase letter."
            return
        elif not re.search(r'[A-Z]', password):
            self.errors["password"] = "Password must contain at least one uppercase letter."
            return
        elif not re.search(r'\d', password):
            self.errors["password"] = "Password must contain at least one digit."
            return

class CourseCategoryDataValidator:
    def __init__(self, data, fields=None, exclude_user_id=None, empty_validation=None, null_validation=None):
        self.data = data
        self.fields = fields or ["name", "description", "color", "icon"]
        self.exclude_user_id = exclude_user_id
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "name" in self.fields:
            self.validate_name()
        if "description" in self.fields:
            self.validate_description()
        if "color" in self.fields:
            self.validate_color()
        if "icon" in self.fields:
            self.validate_icon()
        return len(self.errors) == 0

    def validate_name(self):
        name = self.data.get("name")

        if self.empty_validation and not name:
            self.errors["name"] = "Name is required."
            return
        if self.null_validation and not name:
            self.errors["name"] = "Name is required."
            return
        if name and not re.match(r'^[a-zA-Z\s]+$', name):
            self.errors["name"] = "Name must contain only letters and spaces."
            return

    def validate_description(self):
        description = self.data.get("description")

        if self.empty_validation and not description:
            self.errors["description"] = "Description is required."
            return
        if self.null_validation and not description:
            self.errors["description"] = "Description is required."
            return
        if description and len(description) > 1000:
            self.errors["description"] = "Description must not exceed 1000 characters."
            return

    def validate_color(self):
        color = self.data.get("color")

        if self.empty_validation and not color:
            self.errors["color"] = "Color is required."
            return
        if self.null_validation and not color:
            self.errors["color"] = "Color is required."
            return
        # Validate hex color code (e.g., #FFFFFF or #FFF)
        if color and not re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', color):
            self.errors["color"] = "Color must be a valid hex color code (e.g., #FFFFFF or #FFF)."
            return

    def validate_icon(self):
        icon = self.data.get("icon")

        if self.empty_validation and not icon:
            self.errors["icon"] = "Icon file is required."
            return
        if self.null_validation and not icon:
            self.errors["icon"] = "Icon file is required."
            return
        if icon:
            # Check if file is empty
            if icon.size == 0:
                self.errors["icon"] = "Uploaded icon file is empty."
                return
            # Optional: Check file size (e.g., max 5MB)
            max_size = 5 * 1024 * 1024  # 5MB in bytes
            if icon.size > max_size:
                self.errors["icon"] = "Icon file size must not exceed 5MB."
                return
            # Optional: Check file extension
            allowed_extensions = ['jpg', 'jpeg', 'png', 'svg']
            extension = icon.name.split('.')[-1].lower()
            if extension not in allowed_extensions:
                self.errors["icon"] = f"Icon file must be one of: {', '.join(allowed_extensions)}."
            return

class CourseDataValidator:
    def __init__(self, data, fields=None, exclude_user_id=None, empty_validation=None, null_validation=None):
        self.data = data
        self.fields = fields or ["title", "thumbnail", "overview", "description", "objectives", "intro", "level", "certificate", "language"]
        self.exclude_user_id = exclude_user_id
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "title" in self.fields:
            self.validate_title()
        if "thumbnail" in self.fields:
            self.validate_thumbnail()
        if "overview" in self.fields:
            self.validate_overview()
        if "description" in self.fields:
            self.validate_description()
        if "objectives" in self.fields:
            self.validate_objectives()
        if "intro" in self.fields:
            self.validate_intro()
        if "level" in self.fields:
            self.validate_level()
        if "certificate" in self.fields:
            self.validate_certificate()
        if "language" in self.fields:
            self.validate_language()
        return not self.errors

    def validate_title(self):
        title = self.data.get("title")

        if self.empty_validation and not title:
            self.errors["title"] = "Title is required."
            return
        if self.null_validation and not title:
            self.errors["title"] = "Title is required."
            return
        if title and not re.match(r'^[a-zA-Z0-9\s]+$', title):
            self.errors["title"] = "Title must contain only letters and spaces."
            return
        return

    def validate_thumbnail(self):
        thumbnail = self.data.get("thumbnail")
        if self.empty_validation and not thumbnail:
            self.errors["thumbnail"] = "Thumbnail file is required."
            return
        if thumbnail:
            if thumbnail.size == 0:
                self.errors["thumbnail"] = "Uploaded thumbnail file is empty."
        return

    def validate_overview(self):
        overview = self.data.get("overview")
        
        if self.empty_validation and not overview:
            self.errors["overview"] = "Overview is required."
            return
        if self.null_validation and not overview:
            self.errors["overview"] = "Overview is required."
            return
        return

    def validate_description(self):
        description = self.data.get("description")
        
        if self.empty_validation and not description:
            self.errors["description"] = "Description is required."
            return
        if self.null_validation and not description:
            self.errors["description"] = "Description is required."
            return
        return

    def validate_objectives(self):
        objectives = self.data.get("objectives")

        if self.empty_validation and len(objectives) == 0:
            self.errors["objectives"] = "Objectives is required."
            return
        if self.null_validation and len(objectives) == 0:
            self.errors["objectives"] = "Objectives is required."
            return
        return

    def validate_intro(self):
        intro = self.data.get("intro")
        
        if self.empty_validation and not intro:
            self.errors["intro"] = "Intro is required."
            return
        if self.null_validation and not intro:
            self.errors["intro"] = "Intro is required."
            return
        if self.empty_validation and not re.match(r'^[0-9]+$', intro):
            self.errors["intro"] = "Intro must contain only digits."
            return
        return

    def validate_level(self):
        level = self.data.get("level")
        
        if self.empty_validation and not level:
            self.errors["level"] = "Level is required."
            return
        if self.null_validation and not level:
            self.errors["level"] = "Level is required."
            return
        return

    def validate_certificate(self):
        certificate = self.data.get("certificate")
        
        if self.empty_validation and not certificate:
            self.errors["certificate"] = "Certificate is required."
            return
        if self.null_validation and not certificate:
            self.errors["certificate"] = "Certificate is required."
            return
        if certificate and not certificate in ["yes", "no"]:
            self.errors["certificate"] = "Certificate value is either Yes or NO."
            return
        return
    
    def validate_language(self):
        language = self.data.get("language")
        
        if self.empty_validation and not language:
            self.errors["language"] = "Language is required."
            return
        if self.null_validation and not language:
            self.errors["language"] = "Language is required."
            return
        return

class CourseLessonDataValidator:
    def __init__(self, data, fields=None, empty_validation=None, null_validation=None):
        self.data = data
        self.fields = fields or ["title", "course", "thumbnail", "duration", "description", "video_id"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "title" in self.fields:
            self.validate_title()
        if "course" in self.fields:
            self.validate_course()
        if "thumbnail" in self.fields:
            self.validate_thumbnail()
        if "duration" in self.fields:
            self.validate_duration()
        if "description" in self.fields:
            self.validate_description()
        if "video_id" in self.fields:
            self.validate_video_id()
        return not self.errors

    def validate_title(self):
        title = self.data.get("title")

        if self.empty_validation and not title:
            self.errors["title"] = "Title is required."
            return
        if self.null_validation and not title:
            self.errors["title"] = "Title is required."
            return
        if title and not re.match(r'^[a-zA-Z0-9\s]+$', title):
            self.errors["title"] = "Title must contain only letters, numbers and spaces."
        return

    def validate_course(self):
        course = self.data.get("course")

        if self.null_validation and course is None:
            self.errors["course"] = "Course reference is required."
        return

    def validate_thumbnail(self):
        thumbnail = self.data.get("thumbnail")
        if thumbnail:
            if hasattr(thumbnail, 'size') and thumbnail.size == 0:
                self.errors["thumbnail"] = "Uploaded thumbnail file is empty."
        elif self.empty_validation:
            self.errors["thumbnail"] = "Thumbnail is required."
        return

    def validate_duration(self):
        duration = self.data.get("duration")
        if self.empty_validation and not duration:
            self.errors["duration"] = "Duration is required."
            return
        if self.null_validation and not duration:
            self.errors["duration"] = "Duration is required."
            return
        if duration:
            try:
                float(duration)
            except ValueError:
                self.errors["duration"] = "Duration must be a valid number."
        return

    def validate_description(self):
        description = self.data.get("description")
        if self.empty_validation and not description:
            self.errors["description"] = "Description is required."
            return
        if self.null_validation and not description:
            self.errors["description"] = "Description is required."
            return
        return

    def validate_video_id(self):
        video_id = self.data.get("video_id")
        if self.empty_validation and not video_id:
            self.errors["video_id"] = "Video id is required."
            return
        if self.null_validation and not video_id:
            self.errors["video_id"] = "Video id is required."
            return
        if video_id and not re.match(r'[0-9]+$', video_id):
            self.errors["video_id"] = "Video id must be a valid number."
        return

class CourseReviewDataValidator:
    def __init__(self, data, fields=None, exclude_user_id=None, empty_validation=None, null_validation=None):
        self.data = data
        self.fields = fields or ["user", "course", "rate", "review"]
        self.exclude_user_id = exclude_user_id
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "user" in self.fields:
            self.validate_user()
        if "course" in self.fields:
            self.validate_course()
        if "rate" in self.fields:
            self.validate_rate()
        if "review" in self.fields:
            self.validate_review()
        return not self.errors

    def validate_user(self):
        user = self.data.get("user")

        if self.empty_validation and not user:
            self.errors["user"] = "User is required."
            return
        if self.null_validation and not user:
            self.errors["user"] = "User is required."
            return
        if self.exclude_user_id and user == self.exclude_user_id:
            self.errors["user"] = "This user ID is excluded."
            return

    def validate_course(self):
        course = self.data.get("course")

        if self.empty_validation and not course:
            self.errors["course"] = "Course is required."
            return
        if self.null_validation and not course:
            self.errors["course"] = "Course is required."
            return

    def validate_rate(self):
        rate = self.data.get("rate")

        if self.empty_validation and not rate:
            self.errors["rate"] = "Rate is required."
            return
        if self.null_validation and not rate:
            self.errors["rate"] = "Rate is required."
            return

        try:
            if rate:
                rate_value = float(rate)
                if not (1 <= rate_value <= 5):
                    self.errors["rate"] = "Rate must be between 1 and 5."
        except (ValueError, TypeError):
            self.errors["rate"] = "Rate must be a valid number."

    def validate_review(self):
        review = self.data.get("review")

        if self.empty_validation and not review:
            self.errors["review"] = "Review is required."
            return
        if self.null_validation and not review:
            self.errors["review"] = "Review is required."
            return
        if review and len(review) > 1000:
            self.errors["review"] = "Review must not exceed 1000 characters."

class MealPlanDataValidator:
    def __init__(self, data, fields=None, empty_validation=None, null_validation=None):
        self.data = data
        self.fields = fields or ["name", "overview", "description", "thumbnail", "course", "intro"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "name" in self.fields:
            self.validate_name()
        if "overview" in self.fields:
            self.validate_overview()
        if "description" in self.fields:
            self.validate_description()
        if "thumbnail" in self.fields:
            self.validate_thumbnail()
        if "course" in self.fields:
            self.validate_course()
        if "intro" in self.fields:
            self.validate_intro()
        return not self.errors

    def validate_name(self):
        name = self.data.get("name")
        if self.empty_validation and not name:
            self.errors["name"] = "Meal plan name is required."
            return
        if self.null_validation and not name:
            self.errors["name"] = "Meal plan name is required."
            return
        if name and not re.match(r'^[a-zA-Z0-9\s]+$', name):
            self.errors["name"] = "Name must contain only letters, numbers, and spaces."
        return

    def validate_overview(self):
        overview = self.data.get("overview")
        if self.empty_validation and not overview:
            self.errors["overview"] = "Overview is required."
            return
        if self.null_validation and not overview:
            self.errors["overview"] = "Overview is required."
            return
        return

    def validate_description(self):
        description = self.data.get("description")
        if self.empty_validation and not description:
            self.errors["description"] = "Description is required."
            return
        if self.null_validation and not description:
            self.errors["description"] = "Description is required."
            return
        return

    def validate_thumbnail(self):
        thumbnail = self.data.get("thumbnail")
        if thumbnail:
            if hasattr(thumbnail, 'size') and thumbnail.size == 0:
                self.errors["thumbnail"] = "Uploaded thumbnail file is empty."
        elif self.empty_validation:
            self.errors["thumbnail"] = "Thumbnail is required."
        return

    def validate_course(self):
        course = self.data.get("course")

        if self.null_validation and course is None:
            self.errors["course"] = "Course reference is required."
        return

    def validate_intro(self):
        intro = self.data.get("intro")

        if self.empty_validation and not intro:
            self.errors["intro"] = "Intro is required."
            return
        if self.null_validation and not intro:
            self.errors["intro"] = "Intro is required."
            return
        if self.empty_validation and not re.match(r'^[0-9]+$', intro):
            self.errors["intro"] = "Intro must contain only digits."
            return
        return

class MealPlanRecipeValidator:
    def __init__(self, data, fields=None, empty_validation=None, null_validation=None):
        self.data = data
        self.fields = fields or ["name", "plan", "description", "thumbnail", "video", "duration"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "name" in self.fields:
            self.validate_name()
        if "plan" in self.fields:
            self.validate_plan()
        if "description" in self.fields:
            self.validate_description()
        if "thumbnail" in self.fields:
            self.validate_thumbnail()
        if "video" in self.fields:
            self.validate_video()
        if "duration" in self.fields:
            self.validate_duration()
        return not self.errors

    def validate_name(self):
        name = self.data.get("name")
        if self.empty_validation and not name:
            self.errors["name"] = "Name is required."
            return
        if self.null_validation and name is None:
            self.errors["name"] = "Name cannot be null."
            return
        if name and not re.match(r'^[a-zA-Z0-9\s]+$', name):
            self.errors["name"] = "Name must contain only letters, numbers, and spaces."
        return

    def validate_plan(self):
        plan = self.data.get("plan")
        if self.empty_validation and not plan:
            self.errors["plan"] = "Plan is required."
            return
        if self.null_validation and plan is None:
            self.errors["plan"] = "Plan cannot be null."
        return

    def validate_description(self):
        description = self.data.get("description")
        if self.empty_validation and not description:
            self.errors["description"] = "Description is required."
            return
        if self.null_validation and description is None:
            self.errors["description"] = "Description cannot be null."
        return

    def validate_thumbnail(self):
        thumbnail = self.data.get("thumbnail")
        if thumbnail:
            if hasattr(thumbnail, 'size') and thumbnail.size == 0:
                self.errors["thumbnail"] = "Uploaded thumbnail file is empty."
        elif self.empty_validation:
            self.errors["thumbnail"] = "Thumbnail is required."
        return

    def validate_video(self):
        video = self.data.get("video")
        if self.empty_validation and not video:
            self.errors["video"] = "Video is required."
            return
        if self.null_validation and not video:
            self.errors["video"] = "Video is required."
            return
        if video and not re.match(r'[0-9]+$', video):
            self.errors["video"] = "Video must be a valid number."
        return

    def validate_duration(self):
        duration = self.data.get("duration")
        if self.empty_validation and not duration:
            self.errors["duration"] = "Duration is required."
            return
        if self.null_validation and not duration:
            self.errors["duration"] = "Duration is required."
            return
        if duration:
            try:
                float(duration)
            except ValueError:
                self.errors["duration"] = "Duration must be a valid number."
        return

class AudiobookCategoryValidator:
    def __init__(self, data, fields=None, empty_validation=None, null_validation=None):
        self.data = data
        self.fields = fields or ["name", "description", "color", "icon"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "name" in self.fields:
            self.validate_name()
        if "description" in self.fields:
            self.validate_description()
        if "icon" in self.fields:
            self.validate_icon()
        if "color" in self.fields:
            self.validate_color()
        return not self.errors

    def validate_name(self):
        name = self.data.get("name")
        if self.empty_validation and not name:
            self.errors["name"] = "Name is required."
            return
        if self.null_validation and name is None:
            self.errors["name"] = "Name cannot be null."
            return
        if name and not re.match(r'^[a-zA-Z0-9\s]+$', name):
            self.errors["name"] = "Name must contain only letters, numbers, and spaces."
        return

    def validate_description(self):
        description = self.data.get("description")
        if self.empty_validation and not description:
            self.errors["description"] = "Description is required."
            return
        if self.null_validation and description is None:
            self.errors["description"] = "Description cannot be null."
        return

    def validate_icon(self):
        icon = self.data.get("icon")
        if icon:
            if hasattr(icon, 'size') and icon.size == 0:
                self.errors["thumbnail"] = "Uploaded icon file is empty."
        elif self.empty_validation:
            self.errors["thumbnail"] = "Icon is required."
        return

    def validate_color(self):
        color = self.data.get("color")
        if self.empty_validation and not color:
            self.errors["color"] = "Color is required."
            return
        if self.null_validation and not color:
            self.errors["color"] = "Color is required."
        return

class AudiobookValidator:
    def __init__(self, data, fields=None, empty_validation=None, null_validation=None):
        self.data = data
        self.fields = fields or ["title", "overview", "description", "thumbnail", "category", "audio"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "title" in self.fields:
            self.validate_title()
        if "overview" in self.fields:
            self.validate_overview()
        if "description" in self.fields:
            self.validate_description()
        if "thumbnail" in self.fields:
            self.validate_thumbnail()
        if "category" in self.fields:
            self.validate_category()
        if "audio" in self.fields:
            self.validate_audio()
        return not self.errors

    def validate_title(self):
        title = self.data.get("title")
        if self.empty_validation and not title:
            self.errors["title"] = "Title is required."
            return
        if self.null_validation and title is None:
            self.errors["title"] = "Title cannot be null."
            return
        if title and not re.match(r'^[a-zA-Z0-9\s]+$', title):
            self.errors["title"] = "Title must contain only letters, numbers, and spaces."
        return

    def validate_overview(self):
        overview = self.data.get("overview")
        if self.empty_validation and not overview:
            self.errors["overview"] = "Overview is required."
            return
        if self.null_validation and overview is None:
            self.errors["overview"] = "Overview cannot be null."
        return

    def validate_description(self):
        description = self.data.get("description")
        if self.empty_validation and not description:
            self.errors["description"] = "Description is required."
            return
        if self.null_validation and description is None:
            self.errors["description"] = "Description cannot be null."
        return

    def validate_thumbnail(self):
        thumbnail = self.data.get("thumbnail")
        if thumbnail:
            if hasattr(thumbnail, 'size') and thumbnail.size == 0:
                self.errors["thumbnail"] = "Uploaded thumbnail file is empty."
        elif self.empty_validation:
            self.errors["thumbnail"] = "Thumbnail is required."
        return

    def validate_category(self):
        category = self.data.get("category")
        if self.empty_validation and not category:
            self.errors["category"] = "Category is required."
            return
        if self.null_validation and category is None:
            self.errors["category"] = "Category cannot be null."
        return

    def validate_audio(self):
        audio = self.data.get("audio")
        if audio:
            if hasattr(audio, 'size') and audio.size == 0:
                self.errors["audio"] = "Uploaded audio file is empty."
        elif self.empty_validation:
            self.errors["audio"] = "Audio file is required."
        return

class ItemCategoryValidator:
    def __init__(self, data, fields=None, empty_validation=None, null_validation=None):
        self.data = data
        self.fields = fields or ["name", "description", "category-measurement", "color", "icon"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "name" in self.fields:
            self.validate_name()
        if "description" in self.fields:
            self.validate_description()
        if "category-measurement" in self.fields:
            self.validate_measurement()
        if "icon" in self.fields:
            self.validate_icon()
        if "color" in self.fields:
            self.validate_color()
        return not self.errors

    def validate_name(self):
        name = self.data.get("name")
        if self.empty_validation and not name:
            self.errors["name"] = "Name is required."
            return
        if self.null_validation and name is None:
            self.errors["name"] = "Name cannot be null."
            return
        if name and not re.match(r'^[a-zA-Z0-9\s]+$', name):
            self.errors["name"] = "Name must contain only letters, numbers, and spaces."
        return

    def validate_description(self):
        description = self.data.get("description")
        if self.empty_validation and not description:
            self.errors["description"] = "Description is required."
            return
        if self.null_validation and description is None:
            self.errors["description"] = "Description cannot be null."
        return

    def validate_measurement(self):
        measurement = self.data.get("category-measurement")
        if self.empty_validation and not measurement:
            self.errors["category-measurement"] = "Measurement is required."
            return
        if self.null_validation and measurement is None:
            self.errors["category-measurement"] = "Measurement cannot be null."
        return

    def validate_icon(self):
        icon = self.data.get("icon")
        if icon:
            if hasattr(icon, 'size') and icon.size == 0:
                self.errors["icon"] = "Uploaded icon file is empty."
        elif self.empty_validation:
            self.errors["icon"] = "Icon is required."
        return

    def validate_color(self):
        color = self.data.get("color")
        if self.empty_validation and not color:
            self.errors["color"] = "Color is required."
            return
        if self.null_validation and color is None:
            self.errors["color"] = "Color cannot be null."
        return

class ItemValidator:
    def __init__(self, data, fields=None, empty_validation=None, null_validation=None):
        self.data = data
        self.fields = fields or [
            "name", "overview", "description", "thumbnail", "category",
            "min-value", "max-value", "size-selection", "price", "quantity"
            "variation_img", "variation_color", "variation_qty"
        ]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "name" in self.fields:
            self.validate_name()
        if "overview" in self.fields:
            self.validate_overview()
        if "description" in self.fields:
            self.validate_description()
        if "thumbnail" in self.fields:
            self.validate_thumbnail()
        if "category" in self.fields:
            self.validate_category()
        if "min-value" in self.fields:
            self.validate_min_value()
        if "max-value" in self.fields:
            self.validate_max_value()
        if "size-selection" in self.fields:
            self.validate_size_selection()
        if "price" in self.fields:
            self.validate_price()
        if "quantity" in self.fields:
            self.validate_quantity()
        if "variation_img" in self.fields:
            self.validate_variation_img()
        if "variation_color" in self.fields:
            self.validate_variation_color()
        if "variation_qty" in self.fields:
            self.validate_variation_qty()
        return not self.errors

    def validate_name(self):
        name = self.data.get("name")
        if self.empty_validation and not name:
            self.errors["name"] = "Name is required."
            return
        if self.null_validation and name is None:
            self.errors["name"] = "Name cannot be null."
            return
        if name and not re.match(r'^[a-zA-Z0-9\s]+$', name):
            self.errors["name"] = "Name must contain only letters, numbers, and spaces."
        return

    def validate_overview(self):
        overview = self.data.get("overview")
        if self.empty_validation and not overview:
            self.errors["overview"] = "Overview is required."
            return
        if self.null_validation and overview is None:
            self.errors["overview"] = "Overview cannot be null."
        return

    def validate_description(self):
        description = self.data.get("description")
        if self.empty_validation and not description:
            self.errors["description"] = "Description is required."
            return
        if self.null_validation and description is None:
            self.errors["description"] = "Description cannot be null."
        return

    def validate_thumbnail(self):
        thumbnail = self.data.get("thumbnail")
        if thumbnail:
            if hasattr(thumbnail, 'size') and thumbnail.size == 0:
                self.errors["thumbnail"] = "Uploaded thumbnail file is empty."
        elif self.empty_validation:
            self.errors["thumbnail"] = "Thumbnail is required."
        return

    def validate_category(self):
        category = self.data.get("category")
        if self.empty_validation and not category:
            self.errors["category"] = "Category is required."
            return
        if self.null_validation and category is None:
            self.errors["category"] = "Category cannot be null."
        return

    def validate_min_value(self):
        value = self.data.get("min-value")
        if self.empty_validation and value in [None, ""]:
            self.errors["min-value"] = "Minimum value is required."
            return
        if self.null_validation and value is None:
            self.errors["min-value"] = "Minimum value cannot be null."
        return

    def validate_max_value(self):
        value = self.data.get("max-value")
        if self.empty_validation and value in [None, ""]:
            self.errors["max-value"] = "Maximum value is required."
            return
        if self.null_validation and value is None:
            self.errors["max-value"] = "Maximum value cannot be null."
        return

    def validate_size_selection(self):
        sizes = self.data.get("size-selection")
        if self.empty_validation and not sizes:
            self.errors["size-selection"] = "Size selection is required."
            return
        if self.null_validation and sizes is None:
            self.errors["size-selection"] = "Size selection cannot be null."
        return

    def validate_price(self):
        price = self.data.get("price")
        if self.empty_validation and price in [None, ""]:
            self.errors["price"] = "Price is required."
            return
        if self.null_validation and price is None:
            self.errors["price"] = "Price cannot be null."
        return

    def validate_quantity(self):
        price = self.data.get("quantity")
        if self.empty_validation and price in [None, ""]:
            self.errors["quantity"] = "Quantity is required."
            return
        if self.null_validation and price is None:
            self.errors["quantity"] = "Quantity cannot be null."
        return

    def validate_variation_img(self):
        image = self.data.get("variation_img")
        if image:
            if hasattr(image, 'size') and image.size == 0:
                self.errors["variation_img"] = "Variation image file is empty."
        elif self.empty_validation:
            self.errors["variation_img"] = "Variation image is required."
        return

    def validate_variation_color(self):
        color = self.data.get("variation_color")
        if self.empty_validation and not color:
            self.errors["variation_color"] = "Variation color is required."
            return
        if self.null_validation and color is None:
            self.errors["variation_color"] = "Variation color cannot be null."
        return

    def validate_variation_qty(self):
        qty = self.data.get("variation_qty")
        if self.empty_validation and qty in [None, ""]:
            self.errors["variation_qty"] = "Variation quantity is required."
            return
        if self.null_validation and qty is None:
            self.errors["variation_qty"] = "Variation quantity cannot be null."
        return

class PaymentMethodValidator:
    def __init__(self, data, fields=None, empty_validation=False, null_validation=False):
        self.data = data
        self.fields = fields or ["name", "icon", "holder", "num"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "name" in self.fields:
            self.validate_name()
        if "icon" in self.fields:
            self.validate_icon()
        if "holder" in self.fields:
            self.validate_holder()
        if "num" in self.fields:
            self.validate_num()
        return not self.errors

    def validate_name(self):
        name = self.data.get("name")
        if self.empty_validation and not name:
            self.errors["name"] = "Name is required."
            return
        if self.null_validation and name is None:
            self.errors["name"] = "Name cannot be null."
            return
        if name and not re.match(r'^[a-zA-Z0-9\s]+$', name):
            self.errors["name"] = "Name must contain only letters, numbers, and spaces."

    def validate_icon(self):
        icon = self.data.get("icon")
        if self.empty_validation and not icon:
            self.errors["icon"] = "Icon is required."
            return
        if self.null_validation and icon is None:
            self.errors["icon"] = "Icon cannot be null."

    def validate_holder(self):
        holder = self.data.get("holder")
        if self.empty_validation and not holder:
            self.errors["holder"] = "Holder is required."
            return
        if self.null_validation and holder is None:
            self.errors["holder"] = "Holder cannot be null."

    def validate_num(self):
        num = self.data.get("num")
        if self.empty_validation and num in [None, ""]:
            self.errors["num"] = "Num is required."
            return
        if self.null_validation and num is None:
            self.errors["num"] = "Num cannot be null."
        elif num and not str(num).isdigit():
            self.errors["num"] = "Num must be a number."

class PackagePlanValidator:
    def __init__(self, data, fields=None, empty_validation=False, null_validation=False):
        self.data = data
        self.fields = fields or ["name", "overview", "price", "entities", "offers"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "name" in self.fields:
            self.validate_name()
        if "overview" in self.fields:
            self.validate_overview()
        if "price" in self.fields:
            self.validate_price()
        if "entities" in self.fields:
            self.validate_entities()
        if "offers" in self.fields:
            self.validate_offers()
        return not self.errors

    def validate_name(self):
        name = self.data.get("name")
        if self.empty_validation and not name:
            self.errors["name"] = "Name is required."
            return
        if self.null_validation and name is None:
            self.errors["name"] = "Name cannot be null."
            return
        if name and not re.match(r'^[a-zA-Z0-9\s]+$', name):
            self.errors["name"] = "Name must contain only letters, numbers, and spaces."

    def validate_overview(self):
        overview = self.data.get("overview")
        if self.empty_validation and not overview:
            self.errors["overview"] = "Overview is required."
            return
        if self.null_validation and overview is None:
            self.errors["overview"] = "Overview cannot be null."

    def validate_price(self):
        price = self.data.get("price")
        if self.empty_validation and price in [None, ""]:
            self.errors["price"] = "Price is required."
            return
        if self.null_validation and price is None:
            self.errors["price"] = "Price cannot be null."
            return
        try:
            float(price)
        except (ValueError, TypeError):
            self.errors["price"] = "Price must be a valid number."

    def validate_entities(self):
        entities = self.data.get("entities")
        if self.empty_validation and not entities:
            self.errors["entities"] = "Entities are required."
            return
        if self.null_validation and entities is None:
            self.errors["entities"] = "Entities cannot be null."

    def validate_offers(self):
        offers = self.data.get("offers")
        if self.empty_validation and not offers:
            self.errors["offers"] = "Offers are required."
            return
        if self.null_validation and offers is None:
            self.errors["offers"] = "Offers cannot be null."

class EcommercePCValidator:
    def __init__(self, data, fields=None, empty_validation=False, null_validation=False):
        self.data = data
        self.fields = fields or [
            "order_id", "user_name", "user_email", "user_phone",
            "items", "price", "method", "proof"
        ]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "order_id" in self.fields:
            self.validate_order_id()
        if "user_name" in self.fields:
            self.validate_user_name()
        if "user_email" in self.fields:
            self.validate_user_email()
        if "user_phone" in self.fields:
            self.validate_user_phone()
        if "items" in self.fields:
            self.validate_items()
        if "price" in self.fields:
            self.validate_price()
        if "method" in self.fields:
            self.validate_method()
        if "proof" in self.fields:
            self.validate_proof()
        return not self.errors

    def validate_order_id(self):
        order_id = self.data.get("order_id")
        if self.empty_validation and not order_id:
            self.errors["order_id"] = "Order ID is required."
            return
        if self.null_validation and order_id is None:
            self.errors["order_id"] = "Order ID cannot be null."

    def validate_user_name(self):
        user_name = self.data.get("user_name")
        if self.empty_validation and not user_name:
            self.errors["user_name"] = "User name is required."
            return
        if self.null_validation and user_name is None:
            self.errors["user_name"] = "User name cannot be null."
            return
        if user_name and not re.match(r'^[a-zA-Z\s]+$', user_name):
            self.errors["user_name"] = "User name must contain only letters and spaces."

    def validate_user_email(self):
        user_email = self.data.get("user_email")
        if self.empty_validation and not user_email:
            self.errors["user_email"] = "Email is required."
            return
        if self.null_validation and user_email is None:
            self.errors["user_email"] = "Email cannot be null."
            return
        if user_email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', user_email):
            self.errors["user_email"] = "Invalid email format."

    def validate_user_phone(self):
        user_phone = self.data.get("user_phone")
        if self.empty_validation and not user_phone:
            self.errors["user_phone"] = "Phone number is required."
            return
        if self.null_validation and user_phone is None:
            self.errors["user_phone"] = "Phone number cannot be null."
            return
        if user_phone and not re.match(r'^\+?\d{7,15}$', user_phone):
            self.errors["user_phone"] = "Invalid phone number format."

    def validate_items(self):
        items = self.data.get("items")
        if self.empty_validation and not items:
            self.errors["items"] = "Items are required."
            return
        if self.null_validation and items is None:
            self.errors["items"] = "Items cannot be null."

    def validate_price(self):
        price = self.data.get("price")
        if self.empty_validation and price in [None, ""]:
            self.errors["price"] = "Price is required."
            return
        if self.null_validation and price is None:
            self.errors["price"] = "Price cannot be null."
            return
        try:
            float(price)
        except (ValueError, TypeError):
            self.errors["price"] = "Price must be a valid number."

    def validate_method(self):
        method = self.data.get("method")
        if self.empty_validation and not method:
            self.errors["method"] = "Method is required."
            return
        if self.null_validation and method is None:
            self.errors["method"] = "Method cannot be null."

    def validate_proof(self):
        proof = self.data.get("proof")
        if self.empty_validation and not proof:
            self.errors["proof"] = "Proof is required."
        if self.null_validation and proof is None:
            self.errors["proof"] = "Proof cannot be null."

class PackagePCValidator:
    def __init__(self, data, fields=None, empty_validation=False, null_validation=False):
        self.data = data
        self.fields = fields or ["package", "email", "method", "proof"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "package" in self.fields:
            self.validate_package()
        if "email" in self.fields:
            self.validate_email()
        if "method" in self.fields:
            self.validate_method()
        if "proof" in self.fields:
            self.validate_proof()
        return not self.errors

    def validate_package(self):
        package = self.data.get("package")
        if self.empty_validation and not package:
            self.errors["package"] = "Package is required."
            return
        if self.null_validation and package is None:
            self.errors["package"] = "Package cannot be null."

    def validate_email(self):
        email = self.data.get("email")
        if self.empty_validation and not email:
            self.errors["email"] = "Email is required."
            return
        if self.null_validation and email is None:
            self.errors["email"] = "Email cannot be null."
            return
        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            self.errors["email"] = "Invalid email format."

    def validate_method(self):
        method = self.data.get("method")
        if self.empty_validation and not method:
            self.errors["method"] = "Payment method is required."
            return
        if self.null_validation and method is None:
            self.errors["method"] = "Payment method cannot be null."
            return
        # Optionally check for allowed method IDs
        # allowed_methods = {1, 2, 3}  # example method IDs
        # if method not in allowed_methods:
        #     self.errors["method"] = "Invalid payment method."

    def validate_proof(self):
        proof = self.data.get("proof")
        if self.empty_validation and not proof:
            self.errors["proof"] = "Proof file is required."
            return
        if self.null_validation and proof is None:
            self.errors["proof"] = "Proof cannot be null."
            return
        if hasattr(proof, 'content_type'):
            if proof.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
                self.errors["proof"] = "Unsupported file type for proof. Allowed: jpg, png, pdf."

class AppointmentValidator:
    def __init__(self, data, fields=None, empty_validation=False, null_validation=False):
        self.data = data
        self.fields = fields or ["customer", "subject", "message", "schedule"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "customer" in self.fields:
            self.validate_customer()
        if "subject" in self.fields:
            self.validate_subject()
        if "message" in self.fields:
            self.validate_message()
        if "schedule" in self.fields:
            self.validate_schedule()
        return not self.errors

    def validate_customer(self):
        customer = self.data.get("customer")
        if self.empty_validation and not customer:
            self.errors["customer"] = "Customer is required."
            return
        if self.null_validation and customer is None:
            self.errors["customer"] = "Customer cannot be null."

    def validate_subject(self):
        subject = self.data.get("subject")
        if self.empty_validation and not subject:
            self.errors["subject"] = "Subject is required."
            return
        if self.null_validation and subject is None:
            self.errors["subject"] = "Subject cannot be null."

    def validate_message(self):
        message = self.data.get("message")
        if self.empty_validation and not message:
            self.errors["message"] = "Message is required."
            return
        if self.null_validation and message is None:
            self.errors["message"] = "Message cannot be null."

    def validate_schedule(self):
        schedule = self.data.get("schedule")
        if self.empty_validation and not schedule:
            self.errors["schedule"] = "Schedule is required."
            return
        if self.null_validation and schedule is None:
            self.errors["schedule"] = "Schedule cannot be null."
