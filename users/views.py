from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import CustomUser  # Your custom user model
from .models import UserProfile 

from .serializers import UserSerializer


class CreateUserView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class CustomTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['username'] = self.user.username
        data['email'] = self.user.email
        # Add more fields if needed (e.g., role, id, etc.)
        return data

class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer

