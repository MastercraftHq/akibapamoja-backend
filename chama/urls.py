from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'chamas', views.ChamaViewSet, basename='chama')

urlpatterns = [
    path('', include(router.urls)),
]