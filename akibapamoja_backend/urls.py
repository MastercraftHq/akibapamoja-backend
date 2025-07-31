from django.contrib import admin
from django.urls import path, include
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from contributions.views import ContributionViewSet


schema_view = get_schema_view(
    openapi.Info(
        title="Akiba Pamoja API",
        default_version='v1',
        description="API documentation for Akiba Pamoja project",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email=""),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=[],
)
router = DefaultRouter()
router.register(r'chamas/(?P<chama_id>\d+)/contributions', ContributionViewSet, basename='contributions')

urlpatterns = [
    path("", schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls),

    path('api/users/', include("users.urls")),
    path('api/', include("chama.urls")),
    path('api/', include(router.urls)),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
