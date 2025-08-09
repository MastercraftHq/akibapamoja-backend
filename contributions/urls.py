from rest_framework.routers import DefaultRouter
from .views import ContributionViewSet

router = DefaultRouter()
router.register(
    r'chamas/(?P<chama_id>\d+)/contributions',
    ContributionViewSet,
    basename='contributions'
)

urlpatterns = router.urls