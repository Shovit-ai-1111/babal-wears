from django.conf import settings
from .models import StoreSettings


def get_store(request):
    if not hasattr(request, "store_settings"):
        request.store_settings = StoreSettings.load()
    return request.store_settings


def brand(request):
    return {"demo_mode": settings.DEMO_MODE, "store": get_store(request), "instagram_url": "https://www.instagram.com/babalwears/", "dm_url": "https://ig.me/babalwears"}
