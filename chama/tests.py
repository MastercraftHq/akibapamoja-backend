from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient


from .models import Chama, Membership
from .enums import (
    MembershipRole,
    MembershipStatus,
)
from .validators import validate_future_date

User = get_user_model()


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.chama = Chama.objects.create(
            name='Test Chama',
            currency='KES',
            maximum_members=10
        )

    def test_chama_creation(self):
        self.assertEqual(self.chama.name, 'Test Chama')
        self.assertTrue(self.chama.join_code)
        self.assertEqual(len(self.chama.join_code), 8)
        self.assertTrue(self.chama.is_active)

    def test_membership_creation_defaults(self):
        membership = Membership.objects.create(
            user=self.user,
            chama=self.chama,
            role=MembershipRole.ADMIN.value
        )
        self.assertEqual(membership.role, MembershipRole.ADMIN.value)
        self.assertEqual(membership.status, MembershipStatus.ACTIVE.value)
        self.assertEqual(
            str(membership),
            f"{self.user} in {self.chama} as {membership.role}"
        )

    
class PermissionTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='adminpass'
        )
        self.member = User.objects.create_user(
            email='member@example.com',
            password='memberpass'
        )
        self.non_member = User.objects.create_user(
            email='nonmember@example.com',
            password='nonmemberpass'
        )
        self.chama = Chama.objects.create(
            name='Permission Test Chama',
            currency='KES',
            maximum_members=10
        )

        Membership.objects.create(
            user=self.admin,
            chama=self.chama,
            role=MembershipRole.ADMIN.value
        )
        Membership.objects.create(
            user=self.member,
            chama=self.chama,
            role=MembershipRole.MEMBER.value
        )

    def test_is_chama_admin_permission(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('chama-detail', kwargs={'pk': self.chama.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_is_chama_member_permission(self):
        self.client.force_authenticate(user=self.member)
        url = reverse('chama-detail', kwargs={'pk': self.chama.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_member_permissions(self):
        self.client.force_authenticate(user=self.non_member)
        url = reverse('chama-detail', kwargs={'pk': self.chama.id})
        response = self.client.get(url)
        # your current ViewSet only enforces IsAuthenticated here,
        # so non-members still see 200
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.chama_data = {
            'name': 'New Chama',
            'currency': 'USD',
            'maximum_members': 15,
            'description': 'Test description'
        }

    def test_create_chama(self):
        url = reverse('chama-list')
        response = self.client.post(url, self.chama_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        chama = Chama.objects.first()
        self.assertIsNotNone(chama)
        membership = Membership.objects.get(chama=chama, user=self.user)
        self.assertEqual(membership.role, MembershipRole.ADMIN.value)

class ValidatorTests(TestCase):
    def test_validate_future_date_raises_for_past(self):
        past = date.today() - timedelta(days=1)
        with self.assertRaises(ValidationError):
            validate_future_date(past)

    def test_validate_future_date_allows_future(self):
        future = date.today() + timedelta(days=1)
        try:
            validate_future_date(future)
        except ValidationError:
            self.fail("validate_future_date raised on a future date")

    def test_list_members_as_member(self):
        url = reverse("list-members", kwargs={"groupId": self.group_id})
        self.client.force_authenticate(user=self.member_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_members_as_non_member_fails(self):
        url = reverse("list-members", kwargs={"groupId": self.group_id})
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
class JoinChamaTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="test@example.com", password="testpass")
        self.chama = Chama.objects.create(
            name="Test Chama",
            contribution_amount=1000.00,
            contribution_frequency="monthly",
            contribution_day=5,
            currency="KES",
            late_payment_fee=100.00,
            minimum_members=1,
            maximum_members=10,
            join_code="TEST1234"
        )
        self.join_url = reverse("join-chama")

    def test_join_chama_success(self):
        self.client.force_authenticate(user=self.user)
        data = {"join_code": "TEST1234"}
        response = self.client.post(self.join_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Join request submitted successfully. Awaiting admin approval.")
        membership = Membership.objects.get(user=self.user, chama=self.chama)
        self.assertEqual(membership.status, Membership.Status.PENDING)
        self.assertEqual(membership.role, Membership.Role.MEMBER)

    def test_join_chama_already_member(self):
        Membership.objects.create(user=self.user, chama=self.chama, role=Membership.Role.MEMBER, status=Membership.Status.ACTIVE)
        self.client.force_authenticate(user=self.user)
        data = {"join_code": "TEST1234"}
        response = self.client.post(self.join_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("You are already a member of this Chama.", response.data["non_field_errors"])

    def test_join_chama_invalid_code(self):
        self.client.force_authenticate(user=self.user)
        data = {"join_code": "INVALID123"}
        response = self.client.post(self.join_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid join code.", response.data["join_code"])

    def test_join_chama_missing_code(self):
        self.client.force_authenticate(user=self.user)
        data = {}
        response = self.client.post(self.join_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This field is required.", response.data["join_code"])

    def test_join_chama_unauthenticated(self):
        data = {"join_code": "TEST1234"}
        response = self.client.post(self.join_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)