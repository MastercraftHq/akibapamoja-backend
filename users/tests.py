from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from users.models import User


class UserTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("users-list")
        self.login_url = reverse("users-login")
        self.me_url = reverse("me-list")
        self.user_data = {
            "name": "Test User",
            "email": "test@example.com",
            "phone": "0712345678",
            "password": "StrongPass123"
        }
        self.user = User.objects.create_user(
            email="existing@example.com",
            phone="0700000000",
            name="Existing",
            password="StrongPass123"
        )

    # --- Registration Tests ---
    def test_register_success_email_only(self):
        data = {
            "name": "EmailOnly",
            "email": "emailonly@example.com",
            "password": "StrongPass123"
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("authToken", response.data)

    def test_register_success_phone_only(self):
        data = {
            "name": "PhoneOnly",
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
            "name": "MissingAll",
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
            "name": "Updated User",
            "phone": "0799999999"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["name"], "Updated User")

    def test_partial_update_profile_success(self):
        self.authenticate()
        patch_url = reverse("me-partial-update")
        response = self.client.patch(patch_url, {
            "name": "Partial Update"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["name"], "Partial Update")

    def test_update_profile_invalid_data(self):
        self.authenticate()
        response = self.client.put(self.me_url, {"email": "not-an-email"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)