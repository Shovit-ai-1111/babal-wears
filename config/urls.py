from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [path("admin/", admin.site.urls), path("", include("studio.urls"))]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "BABAL WEARS / Studio control"
admin.site.site_title = "Babal Studio"
admin.site.index_title = "Make something babal."
