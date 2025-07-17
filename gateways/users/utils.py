from rest_framework_simplejwt.tokens import RefreshToken

def generate_tokens_for_user(user):
    """
    Generates access and refresh tokens for a given user.

    Args:
        user (User): The user instance to generate tokens for.

    Returns:
        dict: A dictionary with 'authToken' and 'refreshToken'.
    """
    refresh = RefreshToken.for_user(user)
    return {
        "authToken": str(refresh.access_token),
        "refreshToken": str(refresh)
    }
