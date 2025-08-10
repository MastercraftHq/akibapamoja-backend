from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import ContributionViewSet, ContributionScheduleViewSet

router = DefaultRouter()
router.register(r'', ContributionViewSet, basename='contributions')

urlpatterns = [
    # Nested schedule endpoints
    path('chamas/<int:chama_id>/schedules/', ContributionScheduleViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='contribution-schedule-list'),
    path('chamas/<int:chama_id>/schedules/<uuid:id>/', ContributionScheduleViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='contribution-schedule-detail'),

    path('', include(router.urls)),
]
