from django.urls import path, include
from rest_framework.routers import DefaultRouter
from gateways.users.views import UserViewSet, MeViewSet

router = DefaultRouter()
router.register(r'auth', UserViewSet, basename='auth')
router.register(r'me', MeViewSet, basename='me')

urlpatterns = [
    path('', include(router.urls)),
]
