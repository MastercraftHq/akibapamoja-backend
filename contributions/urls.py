from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from django.urls import path, include
from .views import ContributionViewSet

# Parent router for chama
parent_router = DefaultRouter()
parent_router.register(r'chamas', None, basename='chama')  # Placeholder, actual ChamaViewSet should be registered in chama/urls.py

# Nested router for contributions under chama
contribution_router = NestedDefaultRouter(parent_router, r'chamas', lookup='chama')
contribution_router.register(r'contributions', ContributionViewSet, basename='chama-contributions')

urlpatterns = [
    path('', include(contribution_router.urls)),
]
