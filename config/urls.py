from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from api.views_share import transformation_share

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("t/<uuid:pk>/", transformation_share, name="transformation-share"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
