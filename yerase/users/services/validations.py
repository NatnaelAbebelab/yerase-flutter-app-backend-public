import re
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from datetime import datetime

class UserAccountDataValidator:
    def __init__(self, data, fields=None, empty_validation=True, null_validation=True):
        self.data = data
        self.fields = fields or [
            "fname", "lname", "email", "phone", "password", "weight", "height", "age", "gender"
        ]
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
        if "password" in self.fields:
            self.validate_password()
        if "weight" in self.fields:
            self.validate_weight()
        if "height" in self.fields:
            self.validate_height()
        if "age" in self.fields:
            self.validate_age()
        if "gender" in self.fields:
            self.validate_gender()
        return not bool(self.errors)

    def validate_fname(self):
        fname = self.data.get("fname")
        if self.empty_validation and not fname:
            self.errors["fname"] = "First name is required."
            return
        if self.null_validation and fname is None:
            self.errors["fname"] = "First name cannot be null."
            return
        if fname and not re.match(r'^[a-zA-Z\s]+$', fname):
            self.errors["fname"] = "First name must contain only letters and spaces."

    def validate_lname(self):
        lname = self.data.get("lname")
        if self.empty_validation and not lname:
            self.errors["lname"] = "Last name is required."
            return
        if self.null_validation and lname is None:
            self.errors["lname"] = "Last name cannot be null."
            return
        if lname and not re.match(r'^[a-zA-Z\s]+$', lname):
            self.errors["lname"] = "Last name must contain only letters and spaces."

    def validate_email(self):
        email = self.data.get("email")
        if self.empty_validation and not email:
            self.errors["email"] = "Email is required."
            return
        if self.null_validation and email is None:
            self.errors["email"] = "Email cannot be null."
            return
        if email:
            try:
                validate_email(email)
            except ValidationError:
                self.errors["email"] = "Invalid email format."

    def validate_phone(self):
        phone = self.data.get("phone")
        if self.empty_validation and not phone:
            self.errors["phone"] = "Phone is required."
            return
        if self.null_validation and phone is None:
            self.errors["phone"] = "Phone cannot be null."
            return
        if phone:
            # Normalize phone by removing spaces and dashes
            normalized_phone = phone.replace(" ", "").replace("-", "")

            # Patterns:
            # International: +2519xxxxxxxx or +2517xxxxxxxx (9 digits after +2519 or +2517)
            # Local: 09xxxxxxxx or 07xxxxxxxx (9 digits after 09 or 07)
            pattern_international = r'^\+251(9\d{8}|7\d{8})$'
            pattern_local = r'^(09\d{8}|07\d{8})$'

            if not (re.match(pattern_international, normalized_phone) or re.match(pattern_local, normalized_phone)):
                self.errors["phone"] = ("Phone must be a valid Ethiopian number starting with +2519, +2517, 09, or 07 "
                                        "followed by 8 digits.")
                return

    def validate_password(self):
        password = self.data.get("password")
        if self.empty_validation and not password:
            self.errors["password"] = "Password is required."
            return
        if self.null_validation and password is None:
            self.errors["password"] = "Password cannot be null."
            return
        if password:
            if len(password) < 8:
                self.errors["password"] = "Password must be at least 8 characters."
            elif not re.search(r'[a-z]', password):
                self.errors["password"] = "Password must contain at least one lowercase letter."
            elif not re.search(r'[A-Z]', password):
                self.errors["password"] = "Password must contain at least one uppercase letter."
            elif not re.search(r'\d', password):
                self.errors["password"] = "Password must contain at least one digit."

    def validate_weight(self):
        weight = self.data.get("weight", 0)
        try:
            if float(weight) < 0:
                self.errors["weight"] = "Weight cannot be negative."
        except (ValueError, TypeError):
            self.errors["weight"] = "Weight must be a number."

    def validate_height(self):
        height = self.data.get("height", 0)
        try:
            height = float(height)
            if height < 0:
                self.errors["height"] = "Height cannot be negative."
        except (ValueError, TypeError):
            self.errors["height"] = "Height must be a number."

    def validate_age(self):
        age = self.data.get("age", 0)
        try:
            age = int(age)
            if age < 0 or age > 120:
                self.errors["age"] = "Age must be between 0 and 120."
        except (ValueError, TypeError):
            self.errors["age"] = "Age must be an integer."

    def validate_gender(self):
        gender = self.data.get("gender", "-")
        if self.empty_validation and not gender:
            self.errors["gender"] = "Gender is required."
        elif gender not in ['M', 'F', 'O', '-']:
            self.errors["gender"] = "Gender must be one of: M (Male), F (Female), O (Other), or '-' (Unspecified)."

class AccountActivationDataValidator:
    def __init__(self, data, fields=None, empty_validation=True, null_validation=True):
        self.data = data
        self.fields = fields or ["otp_code", "email", "password"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "otp_code" in self.fields:
            self.validate_otp_code()
        if "email" in self.fields:
            self.validate_email()
        if "password" in self.fields:
            self.validate_password()
        return not bool(self.errors)

    def validate_otp_code(self):
        otp_code = self.data.get("otp_code")
        if self.null_validation and otp_code is None:
            self.errors["otp_code"] = "OTP code cannot be null."
            return
        if self.empty_validation and not otp_code:
            self.errors["otp_code"] = "OTP code is required."
            return
        if not str(otp_code).isdigit() or len(str(otp_code)) != 5:
            self.errors["otp_code"] = "OTP code must be a 4 or 6 digit number."

    def validate_email(self):
        email = self.data.get("email")
        if self.null_validation and email is None:
            self.errors["email"] = "Email cannot be null."
            return
        if self.empty_validation and not email:
            self.errors["email"] = "Email is required."
            return
        if email:
            try:
                validate_email(email)
            except ValidationError:
                self.errors["email"] = "Invalid email format."

    def validate_password(self):
        password = self.data.get("password")
        if self.null_validation and password is None:
            self.errors["password"] = "Password cannot be null."
            return
        if self.empty_validation and not password:
            self.errors["password"] = "Password is required."
            return
        if password:
            if len(password) < 8:
                self.errors["password"] = "Password must be at least 8 characters."
            elif not re.search(r'[a-z]', password):
                self.errors["password"] = "Password must contain at least one lowercase letter."
            elif not re.search(r'[A-Z]', password):
                self.errors["password"] = "Password must contain at least one uppercase letter."
            elif not re.search(r'\d', password):
                self.errors["password"] = "Password must contain at least one digit."

class AppointmentDataValidator:
    def __init__(self, data, fields=None, empty_validation=True, null_validation=True):
        self.data = data
        self.fields = fields or ["subject", "message", "schedule"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "subject" in self.fields:
            self.validate_subject()
        if "message" in self.fields:
            self.validate_message()
        if "schedule" in self.fields:
            self.validate_schedule()
        return not bool(self.errors)

    def validate_subject(self):
        subject = self.data.get("subject")
        if self.empty_validation and not subject:
            self.errors["subject"] = "Subject is required."
            return
        if self.null_validation and subject is None:
            self.errors["subject"] = "Subject cannot be null."
            return
        if subject and len(subject.strip()) < 3:
            self.errors["subject"] = "Subject must be at least 3 characters."

    def validate_message(self):
        message = self.data.get("message")
        if self.empty_validation and not message:
            self.errors["message"] = "Message is required."
            return
        if self.null_validation and message is None:
            self.errors["message"] = "Message cannot be null."
            return
        if message and len(message.strip()) < 5:
            self.errors["message"] = "Message must be at least 5 characters."

    def validate_schedule(self):
        schedule = self.data.get("schedule")
        if self.empty_validation and not schedule:
            self.errors["schedule"] = "Schedule is required."
            return
        if self.null_validation and schedule is None:
            self.errors["schedule"] = "Schedule cannot be null."
            return
        # try:
        #     datetime.fromisoformat(schedule)
        # except (ValueError, TypeError):
        #     self.errors["schedule"] = "Schedule must be a valid ISO datetime format (e.g., YYYY-MM-DDTHH:MM:SS)."

class ToCartDataValidator():
    def __init__(self, data, fields=None, empty_validation=True, null_validation=True):
        self.data = data
        self.fields = fields or ["item", "quantity", "color", "measurement"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "item" in self.fields:
            self.validate_item()
        if "quantity" in self.fields:
            self.validate_quantity()
        if "color" in self.fields:
            self.validate_color()
        if "measurement" in self.fields:
            self.validate_measurement()
        return not bool(self.errors)

    def validate_item(self):
        item = self.data.get("item")
        if self.empty_validation and not item:
            self.errors["item"] = "Item is required."
            return
        if self.null_validation and item is None:
            self.errors["item"] = "Item cannot be null."
            return
        if item and len(item.strip()) < 2:
            self.errors["item"] = "Item name must be at least 2 characters."

    def validate_quantity(self):
        quantity = self.data.get("quantity")
        if self.empty_validation and not quantity:
            self.errors["quantity"] = "Quantity is required."
            return
        if self.null_validation and quantity is None:
            self.errors["quantity"] = "Quantity cannot be null."
            return
        try:
            quantity = float(quantity)
            if quantity <= 0:
                self.errors["quantity"] = "Quantity must be greater than 0."
        except (ValueError, TypeError):
            self.errors["quantity"] = "Quantity must be a number."

    def validate_color(self):
        color = self.data.get("color")
        if self.empty_validation and not color:
            self.errors["color"] = "Color is required."
            return
        if self.null_validation and color is None:
            self.errors["color"] = "Color cannot be null."
            return
        if color and len(color.strip()) < 2:
            self.errors["color"] = "Color must be at least 2 characters."

    def validate_measurement(self):
        measurement = self.data.get("measurement")
        if self.empty_validation and not measurement:
            self.errors["measurement"] = "Measurement is required."
            return
        if self.null_validation and measurement is None:
            self.errors["measurement"] = "Measurement cannot be null."
            return
        if measurement and len(measurement.strip()) < 1:
            self.errors["measurement"] = "Measurement must be a valid value."

class EcommercePCValidator:
    def __init__(self, data, fields=None, empty_validation=True, null_validation=True):

        self.data = data
        # Use a more descriptive name for 'method_' to avoid Python keyword conflicts
        # and align with common naming conventions.
        self.fields = fields or ["name", "email", "phone", "method", "proof"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):

        if "name" in self.fields:
            self.validate_name()
        if "email" in self.fields:
            self.validate_email()
        if "phone" in self.fields:
            self.validate_phone()
        if "method" in self.fields: # Use 'method' as the key for validation
            self.validate_method()
        if "proof" in self.fields:
            self.validate_proof()
        return not bool(self.errors)

    def validate_name(self):

        name = self.data.get("name")
        if self.null_validation and name is None:
            self.errors["name"] = "Name cannot be null."
            return
        if self.empty_validation and (name is None or not str(name).strip()):
            self.errors["name"] = "Name is required."
            return
        if name and len(str(name).strip()) < 2:
            self.errors["name"] = "Name must be at least 2 characters."

    def validate_email(self):
        email = self.data.get("email")
        if self.null_validation and email is None:
            self.errors["email"] = "Email cannot be null."
            return
        if self.empty_validation and (email is None or not str(email).strip()):
            self.errors["email"] = "Email is required."
            return
        # Basic email regex pattern
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        if email and not email_pattern.match(str(email).strip()):
            self.errors["email"] = "Invalid email format."

    def validate_phone(self):
        phone = self.data.get("phone")
        if self.null_validation and phone is None:
            self.errors["phone"] = "Phone cannot be null."
            return
        if self.empty_validation and (phone is None or not str(phone).strip()):
            self.errors["phone"] = "Phone number is required."
            return
        # Remove any non-digit characters for validation (e.g., spaces, hyphens)
        cleaned_phone = re.sub(r'\D', '', str(phone))
        if not cleaned_phone.isdigit():
            self.errors["phone"] = "Phone number must contain only digits."
        elif len(cleaned_phone) < 7: # Assuming a minimum of 7 digits for a valid phone number
            self.errors["phone"] = "Phone number must be at least 7 digits long."

    def validate_method(self):
        method = self.data.get("method") # Access using 'method' key
        if self.null_validation and method is None:
            self.errors["method"] = "Payment method cannot be null."
            return
        if self.empty_validation and (method is None or not str(method).strip()):
            self.errors["method"] = "Payment method is required."
            return
        if method and len(str(method).strip()) < 2:
            self.errors["method"] = "Payment method must be at least 2 characters."

    def validate_proof(self):
        proof = self.data.get("proof")
        if self.null_validation and proof is None:
            self.errors["proof"] = "Proof cannot be null."
            return
        if self.empty_validation and (proof is None or not str(proof).strip()):
            self.errors["proof"] = "Proof is required."
            return
        if proof and len(str(proof).strip()) < 2:
            self.errors["proof"] = "Proof must be at least 2 characters."

class PackagePCValidator:
    def __init__(self, data, fields=None, empty_validation=True, null_validation=True):
        self.data = data
        self.fields = fields or ["fname", "lname", "email", "phone", "plan", "method", "proof"]
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
        if "plan" in self.fields:
            self.validate_plan()
        if "method" in self.fields:
            self.validate_method()
        if "proof" in self.fields:
            self.validate_proof()
        return not bool(self.errors)

    def validate_fname(self):
        """
        Validates the 'fname' (first name) field.
        Checks for emptiness, null, and minimum length.
        """
        fname = self.data.get("fname")
        if self.null_validation and fname is None:
            self.errors["fname"] = "First name cannot be null."
            return
        if self.empty_validation and (fname is None or not str(fname).strip()):
            self.errors["fname"] = "First name is required."
            return
        if fname and len(str(fname).strip()) < 2:
            self.errors["fname"] = "First name must be at least 2 characters."

    def validate_lname(self):
        lname = self.data.get("lname")
        if self.null_validation and lname is None:
            self.errors["lname"] = "Last name cannot be null."
            return
        if self.empty_validation and (lname is None or not str(lname).strip()):
            self.errors["lname"] = "Last name is required."
            return
        if lname and len(str(lname).strip()) < 2:
            self.errors["lname"] = "Last name must be at least 2 characters."

    def validate_email(self):
        email = self.data.get("email")
        if self.null_validation and email is None:
            self.errors["email"] = "Email cannot be null."
            return
        if self.empty_validation and (email is None or not str(email).strip()):
            self.errors["email"] = "Email is required."
            return
        # Basic email regex pattern
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        if email and not email_pattern.match(str(email).strip()):
            self.errors["email"] = "Invalid email format."

    def validate_phone(self):
        phone = self.data.get("phone")
        if self.null_validation and phone is None:
            self.errors["phone"] = "Phone cannot be null."
            return
        if self.empty_validation and (phone is None or not str(phone).strip()):
            self.errors["phone"] = "Phone number is required."
            return
        # Remove any non-digit characters for validation (e.g., spaces, hyphens)
        cleaned_phone = re.sub(r'\D', '', str(phone))
        if not cleaned_phone.isdigit():
            self.errors["phone"] = "Phone number must contain only digits."
        elif len(cleaned_phone) < 7: # Assuming a minimum of 7 digits for a valid phone number
            self.errors["phone"] = "Phone number must be at least 7 digits long."

    def validate_plan(self):
        plan = self.data.get("plan")
        if self.null_validation and plan is None:
            self.errors["plan"] = "Subscription plan cannot be null."
            return
        if self.empty_validation and (plan is None or not str(plan).strip()):
            self.errors["plan"] = "Subscription plan is required."
            return
        if plan and len(str(plan).strip()) < 2:
            self.errors["plan"] = "Subscription plan must be at least 2 characters."
        # Example of checking against a predefined list of plans (uncomment and modify as needed)
        # valid_plans = ["Basic", "Premium", "Enterprise"]
        # if plan and str(plan).strip() not in valid_plans:
        #     self.errors["plan"] = f"Invalid plan. Must be one of: {', '.join(valid_plans)}."

    def validate_method(self):
        method = self.data.get("method")
        if self.null_validation and method is None:
            self.errors["method"] = "Payment method cannot be null."
            return
        if self.empty_validation and (method is None or not str(method).strip()):
            self.errors["method"] = "Payment method is required."
            return
        if method and len(str(method).strip()) < 2:
            self.errors["method"] = "Payment method must be at least 2 characters."

    def validate_proof(self):
        proof = self.data.get("proof")
        if self.null_validation and proof is None:
            self.errors["proof"] = "Proof cannot be null."
            return
        if self.empty_validation and (proof is None or not str(proof).strip()):
            self.errors["proof"] = "Proof is required."
            return
        if proof and len(str(proof).strip()) < 2:
            self.errors["proof"] = "Proof must be at least 2 characters."

class PlaylistDataValidator:
    def __init__(self, data, fields=None, empty_validation=True, null_validation=True):
        self.data = data
        self.fields = fields or ["name", "audios"]
        self.empty_validation = empty_validation
        self.null_validation = null_validation
        self.errors = {}

    def is_valid(self):
        if "name" in self.fields:
            self.validate_name()
        if "audios" in self.fields:
            self.validate_audios()
        return not bool(self.errors)

    def validate_name(self):
        name = self.data.get("name")
        if self.null_validation and name is None:
            self.errors["name"] = "Name cannot be null."
            return
        if self.empty_validation and (not str(name).strip()):
            self.errors["name"] = "Name is required."
            return
        if len(str(name).strip()) < 2:
            self.errors["name"] = "Name must be at least 2 characters."

    def validate_audios(self):
        audios = self.data.get("audios")
        if self.null_validation and audios is None:
            self.errors["audios"] = "Audios cannot be null."
            return
        if not isinstance(audios, list):
            self.errors["audios"] = "Audios must be a list."
            return
        if self.empty_validation and len(audios) == 0:
            self.errors["audios"] = "Audios list cannot be empty."