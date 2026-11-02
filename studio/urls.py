from django.urls import path
from . import views

app_name = "studio"
urlpatterns = [
    path("", views.designer, name="designer"),
    path("orders/create/", views.order_create, name="order_create"),
    path("orders/<uuid:pk>/done/", views.done, name="done"),
    path("orders/<uuid:pk>/image/", views.order_image, name="order_image"),
    path("staff/payment-proofs/<int:pk>/", views.payment_proof, name="payment_proof"),
    path("explore/", views.explore, name="explore"),
    path("reviews/", views.reviews, name="reviews"),
    path("reviews/submit/", views.review_submit, name="review_submit"),
    path("track/", views.track, name="track"),
    path("health/", views.health, name="health"),
]
