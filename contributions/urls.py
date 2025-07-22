from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ContributionViewSet, mpesa_callback

router = DefaultRouter()
router.register(r'', ContributionViewSet, basename='contributions')

urlpatterns = [
    path('', include(router.urls)),
    path('mpesa-callback/', mpesa_callback, name='mpesa-callback'),
]
