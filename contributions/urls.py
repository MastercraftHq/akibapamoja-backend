from django.urls import path
from .views import ContributionViewSet

urlpatterns = [
    path('', ContributionViewSet.as_view({'get': 'list'}), name='list-contributions'),
]