from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/catalogos/', include('catalogos.urls')),
    path('api/usuarios/', include('usuarios.user_management_urls')),
]

# PROD-1: /media/ y static por Django solo en DEBUG (desarrollo).
# En producción usar endpoints protegidos y storage/proxy controlado.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
