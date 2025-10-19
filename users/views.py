from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, permissions, status, response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken


from users.models import User
from users.serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    UpdateUserSerializer,
    LoginObtainPairSerializer,
    LoginRefreshSerializer,
    LogoutSerializer
)
from users.exceptions import (
    RegistrationError,
    AuthenticationError,
    UpdateError
)
from users.utils import generate_tokens_for_user


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
        serializer.is_valid(raise_exception=True)

        try:
            user = serializer.save()
        except Exception as e:
            raise RegistrationError(detail=str(e))

        refresh = RefreshToken.for_user(user)
        return response.Response({
            "userId": str(user.id),
            "authToken": str(refresh.access_token),
            "refreshToken": str(refresh)
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
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data.get("user")
        tokens = generate_tokens_for_user(user)
        return response.Response(tokens, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method="post",
        request_body=LogoutSerializer,
        responses={200: "Successfully logged out."}
    )
    @action(detail=False, methods=["post"], url_path="logout")
    def logout(self, request):
        """
        Logout user by blacklisting the refresh token.
        """
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        refresh_token = serializer.validated_data.get("refresh")
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as e:
            return response.Response(
                {"error": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return response.Response({
            "message": "Successfully logged out."
        }, status=status.HTTP_200_OK)
        
class LoginObtainPairView(TokenObtainPairView):
    """Obtain JWT tokens with API documentation"""

    serializer_class = LoginObtainPairSerializer

    @swagger_auto_schema(
        request_body=LoginObtainPairSerializer,
        responses={200: "Tokens obtained successfully.", 400: "Invalid credentials."}
    )
    def post(self, request):
        response = super().post(request)
        if response.status_code == status.HTTP_200_OK:
            response.data["message"] = "Tokens obtained successfully."
        return response

class LoginRefreshView(TokenRefreshView):
    """Refresh JWT tokens with API documentation"""

    serializer_class = LoginRefreshSerializer

    @swagger_auto_schema(
        request_body=LoginRefreshSerializer,
        responses={200: "Tokens refreshed successfully.", 400: "Invalid token."}
    )
    def post(self, request):
        response = super().post(request)
        if response.status_code == status.HTTP_200_OK:
            response.data["message"] = "Tokens refreshed successfully."
        return response


class MeViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]  

    @swagger_auto_schema(
        responses={200: UserSerializer}
    )
    def list(self, request):
        """
        Retrieve current user's profile.
        """
        serializer = UserSerializer(request.user)
        return response.Response(serializer.data)

    @swagger_auto_schema(
        request_body=UpdateUserSerializer
    )
    def update(self, request):
        """
        Fully update the logged-in user's profile (PUT).
        """
        return self._save_user(request, partial=False)

    @swagger_auto_schema(
        request_body=UpdateUserSerializer
    )
    def partial_update(self, request):
        """
        Partially update the logged-in user's profile (PATCH).
        """
        return self._save_user(request, partial=True)

    def _save_user(self, request, partial):
        serializer = UpdateUserSerializer(
            request.user, 
            data=request.data, 
            partial=partial,
            context={'request': request}
            )
        serializer.is_valid(raise_exception=True)

        try:
            user = serializer.save()
        except Exception as e:
            raise UpdateError(detail=str(e))

        return response.Response({
            "message": "Profile updated successfully.",
            "user": UserSerializer(user).data
        }, status=status.HTTP_200_OK)