from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import CustomUser, UserProfile

from .serializers import UserSerializer, UserUpdateSerializer


class CreateUserView(generics.CreateAPIView):
    """
    Description: Create a new user account (member or admin).

    Input (JSON): name, email, password, phone, optional groupId.

    Output (JSON): { "userId": "...", "authToken": "..." }.

    Auth: None.

    """
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class CustomTokenSerializer(TokenObtainPairSerializer):
    """
    Serializer for custom token generation.

    This serializer extends the default TokenObtainPairSerializer to include custom fields. 
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        data['username'] = self.user.username
        data['email'] = self.user.email
        # Add more fields if needed (e.g., role, id, etc.)
        return data

class LoginView(TokenObtainPairView):
    """
    Description: Authenticate a user and obtain an access token.

    Input (JSON): email (or phone), password.

    Output (JSON): { "authToken": "...", "refreshToken": "..." }.

    Auth: None.

    """
    serializer_class = CustomTokenSerializer
    permission_classes = [AllowAny]

# New: Update user view
class UpdateUserView(APIView):
    """
    GET: Retrieve the profile of the logged-in user.

    Output (JSON): { "userId", "name", "email", "roles", ... }.

    Auth: Required (Bearer token).


    PUT: Update the profile of the logged-in user.

    Input (JSON): { "name", "email", "roles", ... }.

    Output (JSON): { "userId", "name", "email", "roles", ... }.

    Auth: Required (Bearer token).

    
    PATCH: Update the profile of the logged-in user partially.

    Input (JSON): { "name", "email", "roles", ... }.

    Output (JSON): { "userId", "name", "email", "roles", ... }.
    
    Auth: Required (Bearer token).
 
    """

    def get(self, request):
        serializer = UserUpdateSerializer(request.user)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Your profile was updated successfully.',
                'user': serializer.data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # same as put() since both allow partial updates
    def patch(self, request, *args, **kwargs):
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Your profile was partially updated successfully.',
                'user': serializer.data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
