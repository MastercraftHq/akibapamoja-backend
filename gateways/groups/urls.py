from rest_framework.routers import DefaultRouter
from gateways.groups.views import GroupViewSet

router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='groups')

urlpatterns = router.urls
