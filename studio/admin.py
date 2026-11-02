from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from .models import Order, PaymentOption, PaymentProof, Print, Product, Review, StoreSettings, TShirtColor


class ImageAdmin(admin.ModelAdmin):
    readonly_fields = ("preview",)

    @admin.display(description="Preview")
    def preview(self, obj):
        field = getattr(obj, "image", None) or getattr(obj, "photo", None) or getattr(obj, "qr_image", None)
        if field:
            return format_html('<img src="{}" style="max-width:180px;max-height:180px;object-fit:contain" alt="Image preview">', field.url)
        return "No image"


@admin.register(TShirtColor)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("name", "swatch", "price_adjustment", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    list_filter = ("is_active",)

    @admin.display(description="Color")
    def swatch(self, obj):
        return format_html('<span style="display:inline-block;width:28px;height:28px;border:1px solid #888;background:{}"></span> {}', obj.hex_code, obj.hex_code)


@admin.register(Print)
class PrintAdmin(ImageAdmin):
    list_display = ("name", "preview", "surcharge", "is_active", "is_demo", "sort_order")
    list_filter = ("is_active", "is_demo")
    list_editable = ("is_active", "sort_order")
    search_fields = ("name", "description")


@admin.register(Product)
class ProductAdmin(ImageAdmin):
    list_display = ("name", "category", "preview", "price", "is_active", "is_demo")
    list_filter = ("category", "is_active", "is_demo")
    search_fields = ("name",)


@admin.register(PaymentOption)
class PaymentOptionAdmin(ImageAdmin):
    list_display = ("provider", "account_name", "is_active")


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not StoreSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Review)
class ReviewAdmin(ImageAdmin):
    list_display = ("name", "instagram_username", "rating", "approved", "is_demo", "created_at")
    list_filter = ("approved", "rating", "is_demo")
    search_fields = ("name", "text", "instagram_username")
    actions = ("approve", "unpublish")

    @admin.action(description="Approve selected reviews")
    def approve(self, request, queryset):
        for review in queryset:
            review.approved = True
            review.save(update_fields=["approved"])
            self.log_change(request, review, "Approved review")

    @admin.action(description="Unpublish selected reviews")
    def unpublish(self, request, queryset):
        for review in queryset:
            review.approved = False
            review.save(update_fields=["approved"])
            self.log_change(request, review, "Unpublished review")


class ProofInline(admin.StackedInline):
    model = PaymentProof
    fields = ("proof_link", "submitted_at", "reviewed_at", "reviewed_by", "admin_note")
    readonly_fields = ("proof_link", "submitted_at", "reviewed_at", "reviewed_by")
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Private payment screenshot")
    def proof_link(self, obj):
        return format_html('<a href="{}" target="_blank" rel="noopener">Open payment proof</a>', reverse("studio:payment_proof", args=[obj.pk]))


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "full_name", "phone", "size", "quantity", "total", "payment_method", "payment_status", "status", "created_at")
    list_filter = ("status", "payment_status", "payment_method", "size", "province", "created_at")
    search_fields = ("number", "full_name", "phone", "instagram_username")
    date_hierarchy = "created_at"
    inlines = (ProofInline,)
    exclude = ("generated_image",)
    readonly_fields = ("number", "submission_key", "design_preview", "created_at", "updated_at", "unit_price", "delivery_fee", "total", "payment_status", "color", "print", "color_name", "color_hex", "print_name", "print_scale", "placement", "size", "quantity", "payment_method")
    actions = ("mark_paid", "reject_proof", "mark_shipped")

    def has_add_permission(self, request):
        return False

    @admin.display(description="Design reference (placement and scale are recorded separately)")
    def design_preview(self, obj):
        return format_html('<a href="{0}"><img src="{0}" width="260" alt="Customer design"></a>', reverse("studio:order_image", args=[obj.pk]))

    @admin.action(description="Mark paid after manually checking payment")
    def mark_paid(self, request, queryset):
        with transaction.atomic():
            for order in queryset.select_for_update():
                if order.payment_method != "cod" and not PaymentProof.objects.filter(order=order).exists():
                    self.message_user(request, f"{order.number}: no proof to verify.", messages.WARNING)
                    continue
                order.payment_status = Order.PaymentStatus.PAID
                order.save(update_fields=["payment_status", "updated_at"])
                PaymentProof.objects.filter(order=order).update(reviewed_at=timezone.now(), reviewed_by=request.user)
                self.log_change(request, order, "Payment manually verified")

    @admin.action(description="Reject selected payment proofs")
    def reject_proof(self, request, queryset):
        for order in queryset.exclude(payment_method="cod"):
            order.payment_status = Order.PaymentStatus.REJECTED
            order.save(update_fields=["payment_status", "updated_at"])
            PaymentProof.objects.filter(order=order).update(reviewed_at=timezone.now(), reviewed_by=request.user)
            self.log_change(request, order, "Payment proof rejected")

    @admin.action(description="Mark eligible orders shipped")
    def mark_shipped(self, request, queryset):
        eligible = queryset.exclude(status__in=["cancelled", "delivered"]).filter(Q(payment_method="cod") | Q(payment_status="paid"))
        count = 0
        for order in eligible:
            order.status = Order.Status.SHIPPED
            order.save(update_fields=["status", "updated_at"])
            self.log_change(request, order, "Marked shipped")
            count += 1
        self.message_user(request, f"{count} order(s) marked shipped. Unverified prepaid orders were skipped.")
