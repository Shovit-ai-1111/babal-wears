import secrets
import uuid
from decimal import Decimal
from django.conf import settings
from django.core.files.storage import storages
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator, URLValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from .validators import validate_image, sanitized_image

SIZE_CHOICES = [(x, x) for x in ("S", "M", "L", "XL", "XXL")]
PLACEMENTS = [("chest", "Left chest"), ("center", "Front center"), ("back", "Back")]
PROVINCES = [(x, x) for x in ("Koshi", "Madhesh", "Bagmati", "Gandaki", "Lumbini", "Karnali", "Sudurpashchim")]
PAYMENTS = [("cod", "Cash on delivery"), ("esewa", "eSewa"), ("khalti", "Khalti"), ("fonepay", "FonePay")]


def private_storage():
    return storages["private"]


def order_number():
    return f"BW-{timezone.localdate():%y%m%d}-{secrets.token_hex(5).upper()}"


def instagram_url(value):
    from urllib.parse import urlparse
    URLValidator(schemes=["https"])(value)
    if urlparse(value).hostname not in {"instagram.com", "www.instagram.com"}:
        raise ValidationError("Use an https://www.instagram.com/ post link.")


class CleanImageModel(models.Model):
    image_fields = ()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        for name in self.image_fields:
            field = getattr(self, name)
            if field and not field._committed:
                setattr(self, name, sanitized_image(field))
        super().save(*args, **kwargs)


class StoreSettings(models.Model):
    base_price = models.DecimalField(max_digits=9, decimal_places=2, default=settings.DEFAULT_TSHIRT_PRICE, validators=[MinValueValidator(0)])
    delivery_fee = models.DecimalField(max_digits=9, decimal_places=2, default=settings.DEFAULT_DELIVERY_FEE, validators=[MinValueValidator(0)])
    contact_phone = models.CharField(max_length=30, blank=True)
    delivery_note = models.CharField(max_length=250, default="Delivery availability and timing will be confirmed after your order.")
    size_note = models.TextField(default="Demo sizes S–XXL. Add your garment measurements and fit guidance in admin before launch.")

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def __str__(self):
        return "Store pricing & delivery"


class TShirtColor(models.Model):
    name = models.CharField(max_length=50, unique=True)
    hex_code = models.CharField(max_length=7, validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$", "Use a six-digit hex color.")])
    price_adjustment = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class Print(CleanImageModel):
    image_fields = ("image",)
    name = models.CharField(max_length=80, unique=True)
    image = models.ImageField(upload_to="prints/", validators=[validate_image], help_text="Transparent PNG recommended; JPEG/WebP accepted. Maximum 5 MB.")
    description = models.CharField(max_length=200, blank=True)
    surcharge = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class Product(CleanImageModel):
    image_fields = ("image",)
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=40, default="Other goods")
    description = models.CharField(max_length=250, blank=True)
    image = models.ImageField(upload_to="products/", validators=[validate_image])
    price = models.DecimalField(max_digits=9, decimal_places=2, validators=[MinValueValidator(0)])
    instagram_post_url = models.URLField(blank=True, validators=[instagram_url])
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class PaymentOption(CleanImageModel):
    image_fields = ("qr_image",)
    provider = models.CharField(max_length=12, choices=PAYMENTS[1:], unique=True)
    account_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=80, blank=True)
    qr_image = models.ImageField(upload_to="payment-qr/", blank=True, validators=[validate_image])
    instructions = models.CharField(max_length=250, blank=True)
    is_active = models.BooleanField(default=False)

    def clean(self):
        if self.is_active and not (self.qr_image or self.account_number):
            raise ValidationError("Add an actual payment QR or account number before enabling this method.")

    def __str__(self):
        return self.get_provider_display()


class Order(CleanImageModel):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        CONFIRMED = "confirmed", "Confirmed"
        PRINTING = "printing", "Printing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Pay on delivery"
        REVIEW = "review", "Proof awaiting review"
        PAID = "paid", "Verified paid"
        REJECTED = "rejected", "Proof rejected — contact us"

    image_fields = ("generated_image",)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(max_length=25, default=order_number, unique=True, editable=False)
    submission_key = models.UUIDField(unique=True, editable=False)
    color = models.ForeignKey(TShirtColor, on_delete=models.PROTECT)
    print = models.ForeignKey(Print, on_delete=models.PROTECT)
    color_name = models.CharField(max_length=50)
    color_hex = models.CharField(max_length=7)
    print_name = models.CharField(max_length=80)
    placement = models.CharField(max_length=10, choices=PLACEMENTS)
    print_scale = models.PositiveSmallIntegerField(validators=[MinValueValidator(60), MaxValueValidator(140)])
    generated_image = models.ImageField(storage=private_storage, upload_to="designs/", validators=[validate_image])
    full_name = models.CharField(max_length=100)
    instagram_username = models.CharField(max_length=30, blank=True)
    phone = models.CharField(max_length=10)
    province = models.CharField(max_length=30, choices=PROVINCES)
    district = models.CharField(max_length=80)
    municipality = models.CharField(max_length=100)
    ward = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(35)])
    landmark = models.CharField(max_length=200)
    size = models.CharField(max_length=4, choices=SIZE_CHOICES)
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)])
    notes = models.TextField(blank=True, max_length=1000)
    payment_method = models.CharField(max_length=12, choices=PAYMENTS)
    payment_status = models.CharField(max_length=12, choices=PaymentStatus, default=PaymentStatus.UNPAID)
    status = models.CharField(max_length=12, choices=Status, default=Status.RECEIVED)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=9, decimal_places=2)
    total = models.DecimalField(max_digits=11, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=1, quantity__lte=20), name="order_quantity_range"),
            models.CheckConstraint(condition=models.Q(total__gte=0), name="order_nonnegative_total"),
        ]

    def __str__(self):
        return self.number


class PaymentProof(CleanImageModel):
    image_fields = ("image",)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment_proof")
    image = models.ImageField(storage=private_storage, upload_to="proofs/", validators=[validate_image])
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    admin_note = models.TextField(blank=True)

    def __str__(self):
        return f"Payment proof / {self.order.number}"


class Review(CleanImageModel):
    image_fields = ("photo",)
    name = models.CharField(max_length=80)
    instagram_username = models.CharField(max_length=30, blank=True)
    rating = models.PositiveSmallIntegerField(choices=[(n, str(n)) for n in range(1, 6)], validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField(max_length=1500)
    photo = models.ImageField(upload_to="reviews/", blank=True, validators=[validate_image])
    approved = models.BooleanField(default=False)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name="review_rating_range")]

    def __str__(self):
        return f"{self.name} / {self.rating} stars"


class RateLimitBucket(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
