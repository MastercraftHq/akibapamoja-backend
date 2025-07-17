from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, permissions, status, response
from rest_framework.decorators import action

from gateways.users.models import User
from gateways.users.serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    UpdateUserSerializer
)
from gateways.users.exceptions import (
    RegistrationError,
    AuthenticationError,
    UpdateError
)
from gateways.users.utils import generate_tokens_for_user


class UserViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        request_body=RegisterSerializer,
        responses={201: "User registered successfully.", 400: "Invalid data."}
    )
    def create(self, request):
        """
        Register a new user (Admin or Member).
        """
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            raise RegistrationError(detail=serializer.errors)

        try:
            user = serializer.save()
        except Exception as e:
            raise RegistrationError(detail=str(e))

        tokens = generate_tokens_for_user(user)
        return response.Response({
            "userId": str(user.id),
            **tokens
        }, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        method="post",
        request_body=LoginSerializer,
        responses={200: "Login successful.", 400: "Invalid credentials."}
    )
    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        """
        Authenticate a user and return JWT tokens.
        """
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            raise AuthenticationError(detail=serializer.errors)

        user = serializer.validated_data.get("user")
        if not user:
            raise AuthenticationError(detail="Authentication failed.")

        tokens = generate_tokens_for_user(user)
        return response.Response(tokens, status=status.HTTP_200_OK)


class MeViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(responses={200: UserSerializer})
    def list(self, request):
        """
        Retrieve current user's profile.
        """
        serializer = UserSerializer(request.user)
        return response.Response(serializer.data)

    @swagger_auto_schema(request_body=UpdateUserSerializer)
    def update(self, request):
        """
        Fully update the logged-in user's profile (PUT).
        """
        return self._save_user(request, partial=False)

    @swagger_auto_schema(request_body=UpdateUserSerializer)
    def partial_update(self, request):
        """
        Partially update the logged-in user's profile (PATCH).
        """
        return self._save_user(request, partial=True)

    def _save_user(self, request, partial):
        serializer = UpdateUserSerializer(request.user, data=request.data, partial=partial)
        if not serializer.is_valid():
            raise UpdateError(detail=serializer.errors)

        try:
            user = serializer.save()
        except Exception as e:
            raise UpdateError(detail=str(e))

        return response.Response({
            "message": "Profile updated successfully.",
            "user": UserSerializer(user).data
        }, status=status.HTTP_200_OK)
