from rest_framework_simplejwt.tokens import RefreshToken

def generate_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "authToken": str(refresh.access_token),
        "refreshToken": str(refresh)
    }