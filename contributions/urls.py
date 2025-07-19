from django.urls import path
from .views import ContributionViewSet

app_name = 'contributions'

urlpatterns = [
    path('', ContributionViewSet.as_view({'get': 'list'}), name='list-contributions'),
]