from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch, Mock
from users.utils import send_otp, verify_otp, generate_otp_code
from users.models import User, OTP, SMSDevice
from users.exceptions import OTPSendError
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache


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
            "phone": "0700000000",
            "password": "StrongPass123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("message", response.data)

    def test_obtain_pair_failure_invalid_credentials(self):
        response = self.client.post(self.obtain_pair_url, {
            "phone": "0700000000",
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

class OTPTests(APITestCase):
    def setUp(self):
        self.send_url = reverse("otp-send")
        self.verify_url = reverse("otp-verify")
        self.test_phone = "0712345678"
        self.test_purpose = "login"
        self.test_otp_code = "123456"

    @patch("users.utils.send_otp")
    def test_send_otp_success(self, mock_send_otp):
        mock_send_otp.return_value = True
        data = {"phone": self.test_phone, "purpose": self.test_purpose}
        response = self.client.post(self.send_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "OTP sent successfully.")
        mock_send_otp.assert_called_once_with(self.test_phone, purpose=self.test_purpose)

    def test_send_otp_failure_invalid_data(self):
        data = {"purpose": self.test_purpose}  # Missing phone
        response = self.client.post(self.send_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone", response.data)

    @patch("users.utils.send_otp")
    def test_send_otp_failure_exception(self, mock_send_otp):
        mock_send_otp.side_effect = Exception("Twilio error")
        data = {"phone": self.test_phone, "purpose": self.test_purpose}
        response = self.client.post(self.send_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "Twilio error")

    @patch("users.utils.verify_otp")
    def test_verify_otp_success(self, mock_verify_otp):
        mock_verify_otp.return_value = True
        data = {"phone": self.test_phone, "otp_code": self.test_otp_code, "purpose": self.test_purpose}
        response = self.client.post(self.verify_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "OTP verified successfully.")
        mock_verify_otp.assert_called_once_with(self.test_phone, self.test_otp_code, purpose=self.test_purpose)

    @patch("users.utils.verify_otp")
    def test_verify_otp_failure_invalid_otp(self, mock_verify_otp):
        mock_verify_otp.return_value = False
        data = {"phone": self.test_phone, "otp_code": self.test_otp_code, "purpose": self.test_purpose}
        response = self.client.post(self.verify_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "Invalid OTP.")

    def test_verify_otp_failure_invalid_data(self):
        data = {"phone": self.test_phone, "purpose": self.test_purpose}  # Missing otp_code
        response = self.client.post(self.verify_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("otp_code", response.data)

    @override_settings(TWILIO_ACCOUNT_SID='test', TWILIO_AUTH_TOKEN='test', TWILIO_PHONE_NUMBER='+123')
    @patch('twilio.rest.Client.messages')
    def test_send_otp_integration(self, mock_messages):
        mock_messages.create.return_value = Mock(sid='test_sid')
        data = {"phone": self.test_phone, "purpose": self.test_purpose}
        response = self.client.post(self.send_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(SMSDevice.objects.filter(phone_number=self.test_phone).exists())
        self.assertTrue(OTP.objects.filter(phone=self.test_phone, purpose=self.test_purpose).exists())

    def test_verify_otp_integration_success(self):
        device = SMSDevice.objects.create(phone_number=self.test_phone)
        otp_code = "123456"
        hashed = make_password(otp_code)
        device.current_token = hashed
        device.token_timestamp = timezone.now()
        device.save()
        OTP.objects.create(phone=self.test_phone, hashed_code=hashed, purpose=self.test_purpose)
        data = {"phone": self.test_phone, "otp_code": otp_code, "purpose": self.test_purpose}
        response = self.client.post(self.verify_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        otp = OTP.objects.get(phone=self.test_phone, purpose=self.test_purpose)
        self.assertTrue(otp.is_used)
        device.refresh_from_db()
        self.assertIsNone(device.current_token)

    def test_verify_otp_integration_expired(self):
        device = SMSDevice.objects.create(phone_number=self.test_phone)
        otp_code = "123456"
        hashed = make_password(otp_code)
        device.current_token = hashed
        device.token_timestamp = timezone.now() - timedelta(minutes=11)
        device.save()
        OTP.objects.create(phone=self.test_phone, hashed_code=hashed, purpose=self.test_purpose)
        data = {"phone": self.test_phone, "otp_code": otp_code, "purpose": self.test_purpose}
        response = self.client.post(self.verify_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid OTP.")

    def test_verify_otp_integration_incorrect_code(self):
        device = SMSDevice.objects.create(phone_number=self.test_phone)
        otp_code = "123456"
        hashed = make_password(otp_code)
        device.current_token = hashed
        device.token_timestamp = timezone.now()
        device.save()
        OTP.objects.create(phone=self.test_phone, hashed_code=hashed, purpose=self.test_purpose)
        data = {"phone": self.test_phone, "otp_code": "wrong", "purpose": self.test_purpose}
        response = self.client.post(self.verify_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Invalid OTP.")


class OTPUtilsTests(TestCase):
    def setUp(self):
        self.phone = "0712345678"
        self.purpose = "login"
        count_key = f"otp:count:{self.phone}"
        cooldown_key = f"otp:cooldown:{self.phone}"
        verify_key = f"otp:verify:{self.phone}"
        cache.delete(count_key)
        cache.delete(cooldown_key)
        cache.delete(verify_key)
        self.user = User.objects.create_user(phone=self.phone, password='test')

    def test_generate_otp_code(self):
        code = generate_otp_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    @patch('users.models.SMSDevice.send_token')
    def test_send_otp_success(self, mock_send):
        mock_send.return_value = True
        result = send_otp(self.phone, purpose=self.purpose)
        self.assertTrue(result)
        device = SMSDevice.objects.get(phone_number=self.phone)
        self.assertIsNotNone(device.current_token)
        otp = OTP.objects.get(phone=self.phone, purpose=self.purpose)
        self.assertTrue(check_password(result, otp.hashed_code))

    def test_send_otp_no_phone(self):
        with self.assertRaises(ValueError):
            send_otp(None)

    @patch('users.models.SMSDevice.send_token')
    def test_send_otp_with_code(self, mock_send):
        mock_send.return_value = True
        result = send_otp(self.phone, otp_code="654321", purpose=self.purpose)
        self.assertTrue(result)
        device = SMSDevice.objects.get(phone_number=self.phone)
        self.assertTrue(check_password("654321", device.current_token))
        otp = OTP.objects.get(phone=self.phone, purpose=self.purpose)
        self.assertTrue(check_password("654321", otp.hashed_code))

    @patch('users.models.SMSDevice.send_token')
    def test_send_otp_send_failure(self, mock_send):
        mock_send.return_value = False
        with self.assertRaises(OTPSendError):
            send_otp(self.phone)

    def test_verify_otp_success(self):
        device = SMSDevice.objects.create(phone_number=self.phone)
        otp_code = "123456"
        hashed = make_password(otp_code)
        device.current_token = hashed
        device.token_timestamp = timezone.now()
        device.save()
        OTP.objects.create(phone=self.phone, hashed_code=hashed, purpose=self.purpose)
        result = verify_otp(self.phone, otp_code, self.purpose)
        self.assertTrue(result)
        otp = OTP.objects.get(phone=self.phone, purpose=self.purpose)
        self.assertTrue(otp.is_used)
        device.refresh_from_db()
        self.assertIsNone(device.current_token)

    def test_verify_otp_invalid(self):
        device = SMSDevice.objects.create(phone_number=self.phone)
        device.current_token = make_password("123456")
        device.token_timestamp = timezone.now()
        device.save()
        result = verify_otp(self.phone, "wrong", self.purpose)
        self.assertFalse(result)

    def test_verify_otp_expired(self):
        device = SMSDevice.objects.create(phone_number=self.phone)
        otp_code = "123456"
        hashed = make_password(otp_code)
        device.current_token = hashed
        device.token_timestamp = timezone.now() - timedelta(minutes=11)
        device.save()
        result = verify_otp(self.phone, otp_code, self.purpose)
        self.assertFalse(result)

    def test_verify_otp_no_device(self):
        result = verify_otp("nonexistent", "123456")
        self.assertFalse(result)
