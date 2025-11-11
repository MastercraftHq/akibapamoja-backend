from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import UserViewSet, MeViewSet, LoginObtainPairView, LoginRefreshView, OTPViewSet, ProfilePictureViewSet

router = DefaultRouter()
router.register(r'auth', UserViewSet, basename='auth')


me = MeViewSet.as_view({
    'get': 'list',
    'put': 'update',
    'patch': 'partial_update',
})

urlpatterns = [
    path('me/', me, name='me-profile'),
    path('me/picture/', ProfilePictureViewSet.as_view({'post': 'upload_picture', 'delete': 'delete_picture'}), name='me-picture'),
    path('otp/verify/', OTPViewSet.as_view({'post': 'verify'}), name='otp-verify'),
    path('otp/send/', OTPViewSet.as_view({'post': 'send'}), name='otp-send'),
    path('auth/obtain-pair/', LoginObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', LoginRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]
