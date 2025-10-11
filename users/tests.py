from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.test import override_settings
from users.models import User


class UserTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("auth-list")
        self.login_url = reverse("auth-login")
        self.logout_url = reverse("auth-logout")
        self.obtain_pair_url = reverse("token_obtain_pair")
        self.refresh_url = reverse("token_refresh")
        self.me_url = reverse("me-profile")
        self.user_data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "phone": "0712345678",
            "password": "StrongPass123"
        }
        self.user = User.objects.create_user(
            email="existing@example.com",
            phone="0700000000",
            first_name="Existing",
            last_name="User",
            password="StrongPass123"
        )

    # --- Registration Tests ---

    def test_register_success(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("authToken", response.data)
        self.assertIn("refreshToken", response.data)
        self.assertEqual(response.data["userId"], str(User.objects.get(email=self.user_data["email"]).id))

    def test_register_failure_missing_all_identifiers(self):
        data = {
            "first_name": "Missing",
            "last_name": "All",
            "password": "StrongPass123"
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertIn("phone", response.data)

    def test_register_failure_duplicate_email(self):
        self.user_data["email"] = "existing@example.com"
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    # --- Login Tests ---

    def test_login_success_email(self):
        response = self.client.post(self.login_url, {
            "identifier": "existing@example.com",
            "password": "StrongPass123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("authToken", response.data)
        self.assertIn("refreshToken", response.data)

    def test_login_success_phone(self):
        response = self.client.post(self.login_url, {
            "identifier": "0700000000",
            "password": "StrongPass123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("authToken", response.data)
        self.assertIn("refreshToken", response.data)

    def test_login_failure_invalid_password(self):
        response = self.client.post(self.login_url, {
            "identifier": "existing@example.com",
            "password": "WrongPassword"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_failure_unknown_identifier(self):
        response = self.client.post(self.login_url, {
            "identifier": "unknown@example.com",
            "password": "StrongPass123"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_failure_missing_identifier_or_password(self):
        response = self.client.post(self.login_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_failure_invalid_identifier_format(self):
        response = self.client.post(self.login_url, {
            "identifier": "invalid!@#",
            "password": "StrongPass123"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Logout Tests ---

    def test_logout_success(self):
        self.authenticate()
        response = self.client.post(self.logout_url, {
            "refresh": self.refresh_token
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_logout_failure_invalid_token(self):
        response = self.client.post(self.logout_url, {
            "refresh": "invalid_token"
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Obtain Pair Tests ---

    def test_obtain_pair_success(self):
        response = self.client.post(self.obtain_pair_url, {
            "email": "existing@example.com",
            "password": "StrongPass123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("message", response.data)

    def test_obtain_pair_failure_invalid_credentials(self):
        response = self.client.post(self.obtain_pair_url, {
            "email": "existing@example.com",
            "password": "WrongPassword"
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Refresh Tests ---

    def test_refresh_success(self):
        self.authenticate()
        response = self.client.post(self.refresh_url, {
            "refresh": self.refresh_token
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("message", response.data)

    def test_refresh_failure_invalid_token(self):
        response = self.client.post(self.refresh_url, {
            "refresh": "invalid_token"
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Profile Tests ---

    def authenticate(self):
        response = self.client.post(self.login_url, {
            "identifier": "existing@example.com",
            "password": "StrongPass123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['authToken']}")
        self.refresh_token = response.data['refreshToken']

    def test_get_profile_success(self):
        self.authenticate()
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "existing@example.com")

    def test_get_profile_unauthenticated(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile_success(self):
        self.authenticate()
        response = self.client.put(self.me_url, {
            "first_name": "Updated",
            "last_name": "User",
            "phone": "0799999999"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["user"]["phone"], "0799999999")
        self.assertEqual(response.data["user"]["first_name"], "Updated")

    def test_partial_update_profile_success(self):
        self.authenticate()
        response = self.client.patch(self.me_url, {
            "first_name": "Partial"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["user"]["first_name"], "Partial")

    def test_update_profile_invalid_data(self):
        self.authenticate()
        response = self.client.put(self.me_url, {"email": "not-an-email"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
