import json
import tempfile
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from PIL import Image
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from studio.models import Order, PaymentOption, PaymentProof, Print, Product, Review, StoreSettings, TShirtColor
from studio.payments import gateway, GatewayNotConfigured
from studio.validators import normalize_phone, validate_image


def image_file(name="test.png", size=(80, 80), color="#d5ff45"):
    output = BytesIO()
    Image.new("RGBA", size, color).save(output, "PNG")
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")


class StudioTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.media.cleanup)
        cls.storage_override = override_settings(MEDIA_ROOT=cls.media.name, STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            "private": {"BACKEND": "django.core.files.storage.FileSystemStorage", "OPTIONS": {"location": str(Path(cls.media.name) / "private"), "base_url": "/_private/"}},
        })
        cls.storage_override.enable()
        cls.addClassCleanup(cls.storage_override.disable)

    def setUp(self):
        self.store = StoreSettings.objects.create(base_price=1200, delivery_fee=150)
        self.color = TShirtColor.objects.create(name="Moss", hex_code="#70826B", price_adjustment=50)
        self.art = Print.objects.create(name="Test design", image=image_file(), surcharge=100)
        self.client.get("/")
        self.key = self.client.session["checkout_keys"][-1]

    def order_data(self, **changes):
        data = {
            "submission_key": self.key, "color": self.color.pk, "print": self.art.pk,
            "placement": "center", "print_scale": 100, "full_name": "Test Customer",
            "instagram_username": "@test.person", "phone": "+977 9801234567", "province": "Bagmati",
            "district": "Kathmandu", "municipality": "Kathmandu", "ward": 10, "landmark": "Near the public library",
            "size": "L", "quantity": 2, "notes": "Test only", "payment_method": "cod", "terms": "on",
            "design_image": image_file(), "website": "",
        }
        data.update(changes)
        return data

    def post_order(self, **changes):
        return self.client.post(reverse("studio:order_create"), self.order_data(**changes))

    def test_server_prices_and_snapshot(self):
        response = self.post_order(unit_price="1", total="1", payment_status="paid", status="shipped")
        self.assertEqual(response.status_code, 201, response.content)
        order = Order.objects.get()
        self.assertEqual(order.unit_price, Decimal("1350.00"))
        self.assertEqual(order.total, Decimal("2850.00"))
        self.assertEqual(order.phone, "9801234567")
        self.assertEqual(order.instagram_username, "test.person")
        self.assertEqual(order.status, "received")
        self.assertEqual(order.payment_status, "unpaid")
        self.color.name = "Edited name"
        self.color.save()
        self.assertEqual(order.color_name, "Moss")
        self.assertTrue(order.generated_image.storage.exists(order.generated_image.name))

    def test_retry_is_idempotent(self):
        first = self.post_order()
        second = self.post_order()
        self.assertEqual(first.json()["redirect"], second.json()["redirect"])
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(second.status_code, 200)

    def test_checkout_token_is_session_bound(self):
        other = Client()
        response = other.post(reverse("studio:order_create"), self.order_data())
        self.assertEqual(response.status_code, 422)
        self.assertEqual(Order.objects.count(), 0)

    def test_receipt_and_images_are_private(self):
        response = self.post_order()
        order = Order.objects.get()
        self.assertEqual(self.client.get(response.json()["redirect"]).status_code, 200)
        self.assertEqual(Client().get(response.json()["redirect"]).status_code, 404)
        self.assertEqual(Client().get(reverse("studio:order_image", args=[order.pk])).status_code, 404)
        image = self.client.get(reverse("studio:order_image", args=[order.pk]))
        self.assertEqual(image.status_code, 200)
        self.assertIn("no-store", image["Cache-Control"])
        image.close()

    def test_prepaid_needs_active_provider_and_proof(self):
        response = self.post_order(payment_method="khalti")
        self.assertEqual(response.status_code, 422)
        self.assertIn("payment_method", response.json()["errors"])
        self.assertIn("payment_screenshot", response.json()["errors"])
        PaymentOption.objects.create(provider="khalti", account_name="Test-only account", account_number="TEST", is_active=True)
        response = self.post_order(payment_method="khalti", payment_screenshot=image_file())
        self.assertEqual(response.status_code, 201, response.content)
        order = Order.objects.get()
        self.assertEqual(order.payment_status, "review")
        proof = PaymentProof.objects.get(order=order)
        self.assertNotIn("media/proofs", proof.image.url)
        self.assertEqual(Client().get(reverse("studio:payment_proof", args=[proof.pk])).status_code, 302)
        staff = get_user_model().objects.create_user("limited", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(reverse("studio:payment_proof", args=[proof.pk])).status_code, 404)

    def test_unknown_and_inactive_catalogue_rejected(self):
        response = self.post_order(color=99999)
        self.assertEqual(response.status_code, 422)
        self.art.is_active = False
        self.art.save()
        response = self.post_order()
        self.assertEqual(response.status_code, 422)

    def test_boundaries_and_bad_phone_rejected(self):
        for changes in ({"quantity": 21}, {"quantity": 0}, {"print_scale": 150}, {"ward": 0}, {"phone": "1234567890"}, {"size": "MEGA"}):
            with self.subTest(changes=changes):
                self.assertEqual(self.post_order(**changes).status_code, 422)
        self.assertEqual(Order.objects.count(), 0)

    def test_honeypot_rejects_spam(self):
        response = self.post_order(website="https://spam.invalid")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(Order.objects.count(), 0)

    def test_csrf_enforced(self):
        strict = Client(enforce_csrf_checks=True)
        strict.get("/")
        data = self.order_data(submission_key=strict.session["checkout_keys"][-1])
        self.assertEqual(strict.post(reverse("studio:order_create"), data).status_code, 403)

    def test_rate_limit_persists_across_clients(self):
        for n in range(10):
            response = Client().post(reverse("studio:order_create"), {})
            self.assertEqual(response.status_code, 422)
        response = Client().post(reverse("studio:order_create"), {})
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)

    def test_fake_image_rejected(self):
        fake = SimpleUploadedFile("fake.png", b"<script>alert(1)</script>", content_type="image/png")
        self.assertEqual(self.post_order(design_image=fake).status_code, 422)

    def test_metadata_is_removed(self):
        from PIL.PngImagePlugin import PngInfo
        output = BytesIO()
        info = PngInfo()
        info.add_text("private_metadata", "must disappear")
        Image.new("RGB", (100, 100)).save(output, "PNG", pnginfo=info)
        self.post_order(design_image=SimpleUploadedFile("metadata.png", output.getvalue(), content_type="image/png"))
        order = Order.objects.get()
        with order.generated_image.open("rb") as fp:
            with Image.open(fp) as image:
                self.assertNotIn("private_metadata", image.info)

    def test_review_moderation_and_stats(self):
        response = self.client.post(reverse("studio:review_submit"), {"name": "Customer", "instagram_username": "@real.person", "rating": 5, "text": "Love the design.", "consent": "on", "approved": "on"}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        review = Review.objects.get()
        self.assertFalse(review.approved)
        self.assertNotContains(self.client.get(reverse("studio:reviews")), "Love the design.")
        review.approved = True
        review.save()
        Review.objects.create(name="Demo", text="Not a real review", rating=1, approved=True, is_demo=True)
        page = self.client.get(reverse("studio:reviews"))
        self.assertContains(page, "Love the design.")
        self.assertNotContains(page, "Not a real review")
        self.assertEqual(page.context["stats"]["count"], 1)
        self.assertEqual(page.context["stats"]["average"], 5)

    def test_review_xss_escaped_and_bad_rating_rejected(self):
        Review.objects.create(name="<script>bad</script>", text="<script>alert(1)</script>", rating=5, approved=True)
        response = self.client.get(reverse("studio:reviews"))
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.client.post(reverse("studio:review_submit"), {"name": "Bad", "rating": 6, "text": "Invalid", "consent": "on"})
        self.assertEqual(Review.objects.count(), 1)

    def test_tracking_requires_phone_and_returns_no_address(self):
        self.post_order()
        order = Order.objects.get()
        wrong = self.client.post(reverse("studio:track"), {"number": order.number, "phone": "9800000000"})
        self.assertContains(wrong, "No matching order")
        correct = Client().post(reverse("studio:track"), {"number": order.number.lower(), "phone": order.phone})
        self.assertContains(correct, "Received")
        self.assertNotContains(correct, order.full_name)
        self.assertNotContains(correct, order.landmark)

    def test_explore_filter_and_htmx_fragment(self):
        Product.objects.create(name="Test cap", category="Headwear", image=image_file(), price=500)
        self.assertContains(self.client.get('/explore/?category=Headwear', HTTP_HX_REQUEST="true"), "Test cap")
        self.assertNotContains(self.client.get('/explore/?category=Bags', HTTP_HX_REQUEST="true"), "Test cap")
        self.assertNotContains(self.client.get('/explore/', HTTP_HX_REQUEST="true"), "<!doctype")

    def test_phone_normalization(self):
        self.assertEqual(normalize_phone("९८०१२३४५६७"), "9801234567")
        self.assertEqual(normalize_phone("9779801234567"), "9801234567")
        with self.assertRaises(ValidationError):
            normalize_phone("+919801234567")

    def test_oversized_images_and_requests_rejected(self):
        with self.assertRaises(ValidationError):
            validate_image(SimpleUploadedFile("huge.png", b"x" * (5 * 1024 * 1024 + 1)))
        response = self.client.post(reverse("studio:order_create"), {}, CONTENT_LENGTH=str(13 * 1024 * 1024))
        self.assertEqual(response.status_code, 413)

    def test_admin_shipping_skips_unverified_payment(self):
        from django.contrib.admin.sites import AdminSite
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.test import RequestFactory
        from studio.admin import OrderAdmin
        self.post_order()
        order = Order.objects.get()
        order.payment_method = "khalti"
        order.payment_status = "review"
        order.save()
        user = get_user_model().objects.create_superuser("admin", "admin@example.test", "test-only-password")
        request = RequestFactory().post("/admin/")
        request.user = user
        request.session = self.client.session
        request._messages = FallbackStorage(request)
        order_admin = OrderAdmin(Order, AdminSite())
        order_admin.mark_shipped(request, Order.objects.all())
        order.refresh_from_db()
        self.assertEqual(order.status, "received")
        order.payment_status = "paid"
        order.save()
        order_admin.mark_shipped(request, Order.objects.all())
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")

    def test_disabled_gateway_never_claims_success(self):
        with self.assertRaises(GatewayNotConfigured):
            gateway.verify(reference="not-real", amount_paisa=100)

    def test_public_routes_render_and_health_checks_db(self):
        for url in ("/", "/explore/", "/reviews/", "/track/", "/health/", "/admin/login/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
