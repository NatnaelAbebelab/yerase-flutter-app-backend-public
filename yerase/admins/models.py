from django.db import models
from datetime import datetime
from accounts.models import CustomUser
import uuid
# Create your models here.
class ItemManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class CustomAdmin(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='admin')
    phone = models.CharField(max_length=20, blank=True, null=True)
    otp_code = models.CharField(max_length=20, blank=True, null=True)
    profile = models.CharField(max_length=255, blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    created_by = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.CharField(max_length=255, blank=True, null=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.admin
    
    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class CourseCategory(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    color = models.CharField(max_length=255, blank=True)
    icon = models.CharField(max_length=255, blank=True)
    assigned_course = models.CharField(max_length=255, default='0')
    is_deleted = models.BooleanField(default=False)
    created_on = models.CharField(max_length=255, blank=True)
    updated_on = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return str(self._id)
    
    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class Course(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True)
    category = models.ForeignKey(CourseCategory, on_delete=models.SET_DEFAULT, default=1)
    thumbnail = models.CharField(max_length=255, blank=True, default='default-thumbnail.png')
    overview = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    objectives = models.JSONField(default=list, blank=True)
    intro = models.CharField(max_length=255, blank=True, default='default-intro')
    lesson_count = models.IntegerField(default=0)
    total_duration = models.IntegerField(default=0)
    level = models.CharField(max_length=255, blank=True)
    is_certificated = models.CharField(max_length=255, default='no', blank=True)
    language = models.CharField(max_length=255, default='am', blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return str(self._id)
    
    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class CourseLesson(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True)
    course = models.ForeignKey(Course, on_delete=models.SET_DEFAULT, default=1)
    thumbnail = models.CharField(max_length=255, blank=True, default='default-thumbnail.png')
    duration = models.CharField(max_length=255, blank=True, default='0')
    description = models.CharField(max_length=255, blank=True)
    video_id = models.CharField(max_length=255, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class CourseReview(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active_user = models.CharField(max_length=255, blank=True) # change when users/customers user model is created
    course = models.ForeignKey(Course, on_delete=models.SET_DEFAULT, default=1)
    rate = models.CharField(max_length=255, blank=True, default='5')
    review = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=255, blank=True, default='new')
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class MealPlan(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True)
    overview = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    course = models.ForeignKey(Course, on_delete=models.SET_DEFAULT, default=1)
    thumbnail = models.CharField(max_length=255, blank=True)
    intro = models.CharField(max_length=255, blank=True)
    recipe_count = models.IntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class MealPlanRecipe(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True)
    meal = models.ForeignKey(MealPlan, on_delete=models.SET_DEFAULT, default=1)
    thumbnail = models.CharField(max_length=255, blank=True, default='default-thumbnail.png')
    duration = models.CharField(max_length=255, blank=True, default='0')
    description = models.CharField(max_length=255, blank=True)
    video_link = models.CharField(max_length=255, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class AudiobookCategory(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    color = models.CharField(max_length=255, blank=True)
    icon = models.CharField(max_length=255, blank=True)
    assigned_audio = models.IntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class Audiobook(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True)
    category = models.ForeignKey(AudiobookCategory, on_delete=models.SET_DEFAULT, default=1)
    overview = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    audio = models.CharField(max_length=255, blank=True)
    sliced_audio = models.CharField(max_length=255, blank=True)
    duration = models.CharField(max_length=255, blank=True, default='0')
    thumbnail = models.CharField(max_length=255, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class ItemCategory(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    color = models.CharField(max_length=255, blank=True)
    measurement = models.CharField(max_length=255, blank=True, default='f')
    icon = models.CharField(max_length=255, blank=True)
    item_count = models.IntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class Item(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True)
    category = models.ForeignKey(ItemCategory, on_delete=models.SET_DEFAULT, default=1)
    min_value = models.CharField(max_length=255, blank=True, default='')
    max_value = models.CharField(max_length=255, blank=True, default='')
    sizes = models.JSONField(default=list, blank=True)
    thumbnail = models.CharField(max_length=255, blank=True, default='item-default-thumbnail.png')
    overview = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    variation_img = models.JSONField(default=list, blank=True)
    variation_color = models.JSONField(default=list, blank=True)
    variation_qty = models.JSONField(default=list, blank=True)
    price = models.CharField(max_length=255, blank=True, default='0.00')
    total_purchase_count = models.CharField(max_length=255, default='0')
    quantity = models.CharField(max_length=255, default='0')
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class Cart(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(CustomUser, on_delete=models.SET_DEFAULT, default=1)
    items = models.JSONField(default=list, blank=True)
    quantity = models.JSONField(default=list, blank=True)
    color = models.JSONField(default=list, blank=True)
    measurement = models.JSONField(default=list, blank=True)
    total_price = models.CharField(max_length=255, blank=True, default='0.00')
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class Wishlist(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(CustomUser, on_delete=models.SET_DEFAULT, default=1)
    items = models.JSONField(default=list, blank=True)
    total_price = models.CharField(max_length=255, blank=True, default='0.00')
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class ItemReview(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active_user = models.ForeignKey(CustomUser, on_delete=models.SET_DEFAULT, default=1)
    item = models.ForeignKey(Item, on_delete=models.SET_DEFAULT, default=1)
    rate = models.CharField(max_length=255, blank=True, default='5')
    review = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=255, blank=True, default='new')
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class PaymentMethod(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True)
    account_holder = models.CharField(max_length=255, blank=True)
    account_num = models.CharField(max_length=255, blank=True)
    icon = models.CharField(max_length=255, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class Package(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True)
    overview = models.CharField(max_length=255, blank=True)
    offers = models.JSONField(default=list, blank=True)
    entity = models.JSONField(default=list, blank=True)
    price = models.CharField(max_length=255, blank=True, default='0')
    subscribers = models.CharField(max_length=255, blank=True, default='0')
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class EcommercePC(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.CharField(max_length=255, blank=True)
    user_name = models.ForeignKey(CustomUser, on_delete=models.SET_DEFAULT, default=1)
    user_email = models.CharField(max_length=255, blank=True)
    user_phone = models.CharField(max_length=255, blank=True)
    items = models.JSONField(default=list, blank=True)
    quantity = models.JSONField(default=list, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    proof = models.CharField(max_length=255, blank=True)
    method = models.ForeignKey(PaymentMethod, on_delete=models.SET_DEFAULT, default=1)
    status = models.CharField(max_length=255, blank=True, default='new')
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class PackagePC(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package = models.ForeignKey(Package, on_delete=models.SET_DEFAULT, default=1)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_DEFAULT, default=1)
    price = models.CharField(max_length=255, blank=True)
    proof = models.CharField(max_length=255, blank=True)
    method = models.ForeignKey(PaymentMethod, on_delete=models.SET_DEFAULT, default=1)
    status = models.CharField(max_length=255, blank=True, default='new')
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class Appointment(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=False)
    subject = models.CharField(max_length=255, blank=True)
    message = models.CharField(max_length=255, blank=True)
    schedule = models.CharField(max_length=255, blank=True)
    link = models.CharField(max_length=255, blank=True, default='#')
    status = models.CharField(max_length=255, blank=True, default='new')
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

class Localization(models.Model):
    _id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_key = models.CharField(max_length=255, blank=True)
    content_value = models.CharField(max_length=255, blank=True)
    entity = models.CharField(max_length=255, blank=True, default="content")
    is_deleted = models.BooleanField(default=False)
    created_at = models.CharField(max_length=255, blank=True)
    updated_at = models.CharField(max_length=255, blank=True)
    record_time = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)

    objects = ItemManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()

    def restore(self):
        self.is_deleted = False
        self.updated_at = datetime.today().strftime('%Y-%m-%d')
        self.save()