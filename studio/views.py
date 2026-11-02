import uuid
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db import IntegrityError, connection
from django.db.models import Avg, Count
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .context import get_store
from .forms import OrderForm, ReviewForm, TrackingForm
from .models import Order, PaymentOption, PaymentProof, Print, Product, Review, TShirtColor
from .services import create_order


@require_GET
@never_cache
def designer(request):
    token = str(uuid.uuid4())
    request.session["checkout_keys"] = (request.session.get("checkout_keys", []) + [token])[-10:]
    colors = TShirtColor.objects.filter(is_active=True)
    prints = Print.objects.filter(is_active=True)
    store = get_store(request)
    catalogue = {
        "colors": [{"id": c.pk, "name": c.name, "hex": c.hex_code, "extra": str(c.price_adjustment)} for c in colors],
        "prints": [{"id": p.pk, "name": p.name, "url": p.image.url, "extra": str(p.surcharge), "description": p.description, "demo": p.is_demo} for p in prints],
        "basePrice": str(store.base_price), "delivery": str(store.delivery_fee),
    }
    return render(request, "studio/designer.html", {
        "catalogue": catalogue, "colors": colors, "prints": prints,
        "form": OrderForm(initial={"submission_key": token, "quantity": 1}, checkout_keys=[token]),
        "payment_options": PaymentOption.objects.filter(is_active=True),
    })


@require_POST
@never_cache
def order_create(request):
    keys = request.session.get("checkout_keys", [])
    key = request.POST.get("submission_key", "")
    # A retry after a lost response returns the original order, without a second charge/order.
    existing = Order.objects.filter(submission_key=key).first() if key in keys else None
    if existing:
        order = existing
    else:
        form = OrderForm(request.POST, request.FILES, checkout_keys=keys)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors.get_json_data()}, status=422)
        try:
            order = create_order(form.cleaned_data)
        except (TShirtColor.DoesNotExist, Print.DoesNotExist):
            return JsonResponse({"errors": {"catalogue": [{"message": "This design is no longer available. Reload and choose another."}]}}, status=409)
        except IntegrityError:
            order = Order.objects.filter(submission_key=key).first()
            if order is None:
                raise
    request.session["order_ids"] = (request.session.get("order_ids", []) + [str(order.pk)])[-30:]
    return JsonResponse({"redirect": reverse("studio:done", args=[order.pk]), "order_number": order.number}, status=200 if existing else 201)


def authorized_order(request, pk):
    if not request.user.has_perm("studio.view_order") and str(pk) not in request.session.get("order_ids", []):
        raise Http404
    return get_object_or_404(Order, pk=pk)


@require_GET
@never_cache
def done(request, pk):
    return render(request, "studio/done.html", {"order": authorized_order(request, pk)})


@require_GET
@never_cache
def order_image(request, pk):
    order = authorized_order(request, pk)
    response = FileResponse(order.generated_image.open("rb"), content_type="image/png")
    response["Cache-Control"] = "private, no-store"
    response["Content-Disposition"] = f'inline; filename="{order.number}.png"'
    return response


@staff_member_required
@never_cache
def payment_proof(request, pk):
    if not request.user.has_perm("studio.view_paymentproof"):
        raise Http404
    proof = get_object_or_404(PaymentProof, pk=pk)
    response = FileResponse(proof.image.open("rb"), content_type="image/png")
    response["Cache-Control"] = "private, no-store"
    return response


@require_GET
def explore(request):
    products = Product.objects.filter(is_active=True)
    category = request.GET.get("category", "")
    if category:
        products = products.filter(category=category)
    context = {"products": Paginator(products, 12).get_page(request.GET.get("page")), "category": category,
               "categories": Product.objects.filter(is_active=True).order_by("category").values_list("category", flat=True).distinct()}
    return render(request, "studio/partials/products.html" if request.headers.get("HX-Request") else "studio/explore.html", context)


def review_context(form=None):
    approved = Review.objects.filter(approved=True, is_demo=False)
    return {"reviews": approved, "stats": approved.aggregate(average=Avg("rating"), count=Count("id")),
            "form": form or ReviewForm()}


@require_GET
def reviews(request):
    context = review_context()
    context["reviews"] = Paginator(context["reviews"], 24).get_page(request.GET.get("page"))
    return render(request, "studio/reviews.html", context)


@require_POST
def review_submit(request):
    form = ReviewForm(request.POST, request.FILES)
    success = form.is_valid()
    if success:
        review = form.save(commit=False)
        review.approved = False
        review.save()
        form = ReviewForm()
    if request.headers.get("HX-Request"):
        # A 200 fragment intentionally allows HTMX's default swap on validation errors.
        return render(request, "studio/partials/review_form.html", {"form": form, "submitted": success})
    if success:
        messages.success(request, "Thank you! Your review is waiting for moderation.")
        return redirect("studio:reviews")
    return render(request, "studio/reviews.html", review_context(form), status=400)


@require_http_methods(["GET", "POST"])
@never_cache
def track(request):
    form = TrackingForm(request.POST or None)
    order = None
    if request.method == "POST" and form.is_valid():
        order = Order.objects.filter(number=form.cleaned_data["number"], phone=form.cleaned_data["phone"]).first()
        if order is None:
            form.add_error(None, "No matching order. Check both your order ID and phone number.")
    # Status only: never return address, proof, or customer contact information.
    return render(request, "studio/track.html", {"form": form, "tracked_order": order})


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
