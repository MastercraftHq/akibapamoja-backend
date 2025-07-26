from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import UserViewSet, MeViewSet

router = DefaultRouter()
router.register(r'auth', UserViewSet, basename='auth')


me = MeViewSet.as_view({
    'get': 'list',
    'put': 'update',
    'patch': 'partial_update',
})

urlpatterns = [
    path('', include(router.urls)),
    path('me/', me, name='me-profile'),
]
