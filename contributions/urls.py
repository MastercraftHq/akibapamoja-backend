from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ContributionViewSet

# Simple router for contributions
router = DefaultRouter()
router.register(r'contributions', ContributionViewSet, basename='contributions')

urlpatterns = [
    path('', include(router.urls)),
]
