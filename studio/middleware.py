import hashlib
import time
from datetime import timedelta
from django.conf import settings
from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone
from .models import RateLimitBucket


class RequestGuardMiddleware:
    """Database-backed limits work across Gunicorn workers without Redis."""
    limits = {"/orders/create/": (10, 600), "/reviews/submit/": (5, 3600), "/track/": (20, 600), "/admin/login/": (15, 600)}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST":
            try:
                length = int(request.META.get("CONTENT_LENGTH") or 0)
            except ValueError:
                return HttpResponse("Invalid content length.", status=400)
            if length > settings.REQUEST_BODY_LIMIT:
                return HttpResponse("Upload too large. Each image must be under 5 MB.", status=413)
            if request.path in self.limits:
                limit, window = self.limits[request.path]
                ip = request.META.get("REMOTE_ADDR", "unknown")
                if settings.TRUST_PROXY:
                    ip = request.META.get("HTTP_X_REAL_IP", ip)
                key = hashlib.sha256(f"{request.path}:{ip}:{int(time.time()) // window}".encode()).hexdigest()
                bucket, _ = RateLimitBucket.objects.get_or_create(key=key, defaults={"expires_at": timezone.now() + timedelta(seconds=window)})
                RateLimitBucket.objects.filter(pk=key).update(count=F("count") + 1)
                bucket.refresh_from_db()
                if bucket.count > limit:
                    response = HttpResponse("Too many attempts. Please try again in a few minutes.", status=429)
                    response["Retry-After"] = str(window)
                    return response
        response = self.get_response(request)
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
