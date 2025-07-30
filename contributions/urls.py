# contributions/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContributionViewSet, mpesa_callback

router = DefaultRouter()
router.register(r'contributions', ContributionViewSet, basename='contributions')

urlpatterns = [
     # ViewSet routes (list, retrieve, create, update, etc.)
     path('', include(router.urls)),

     # M-Pesa callback — no auth, used by Safaricom servers
     path('mpesa-callback/', mpesa_callback, name='mpesa-callback'),
     
     # Tests specifically POST here:
     path('api/contributions/mpesa-callback/', mpesa_callback),
 ]

