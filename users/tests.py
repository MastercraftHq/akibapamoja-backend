from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from users.models import User

class UserTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("auth-list")
        self.login_url = reverse("auth-login")
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
    def test_register_success_email_only(self):
        data = {
            "first_name": "Email",
            "last_name": "Only",
            "email": "emailonly@example.com",
            "password": "StrongPass123"
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("authToken", response.data)

    def test_register_success_phone_only(self):
        data = {
            "first_name": "Phone",
            "last_name": "Only",
            "phone": "0722222222",
            "password": "StrongPass123"
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("authToken", response.data)

    def test_register_success_both_email_phone(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("authToken", response.data)

    def test_register_failure_missing_all_identifiers(self):
        data = {
            "first_name": "Missing",
            "last_name": "All",
            "password": "StrongPass123"
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

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

    def test_login_success_phone(self):
        response = self.client.post(self.login_url, {
            "identifier": "0700000000",
            "password": "StrongPass123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("authToken", response.data)

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

    # --- Profile Tests ---
    def authenticate(self):
        response = self.client.post(self.login_url, {
            "identifier": "existing@example.com",
            "password": "StrongPass123"
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['authToken']}")

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
        self.assertEqual(response.data["phone"], "0799999999")
        self.assertEqual(response.data["first_name"], "Updated")

    def test_partial_update_profile_success(self):
        self.authenticate()
        response = self.client.patch(self.me_url, {
            "first_name": "Partial"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Partial")

    def test_update_profile_invalid_data(self):
        self.authenticate()
        response = self.client.put(self.me_url, {"email": "not-an-email"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
