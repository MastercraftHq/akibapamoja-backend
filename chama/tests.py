from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from chama.models import Chama, Membership
from decimal import Decimal

User = get_user_model()

class ChamaEndpointsTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Create users
        self.admin_user = User.objects.create_user(email="admin@example.com", phone="0700000001", password="adminpass")
        self.member_user = User.objects.create_user(email="member@example.com", phone="0700000002", password="memberpass")
        self.other_user = User.objects.create_user(email="out@example.com", phone="0700000003", password="outpass")

        # Log in admin user and create Chama
        self.client.force_authenticate(user=self.admin_user)
        self.create_chama_url = reverse("create-chama")
        self.chama_data = {
            "name": "Savings Squad",
            "description": "Monthly savings group",
            "currency": "KES",
            "minimum_members": 1,
            "maximum_members": 10,
            "join_code": "JOIN1234"
        }
        response = self.client.post(self.create_chama_url, self.chama_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.chama = Chama.objects.first()
        self.chama_id = self.chama.id  # Renamed to chama_id for consistency

        # Add admin membership (created automatically on POST /groups)
        self.admin_membership = Membership.objects.get(user=self.admin_user, chama=self.chama)

        # Add member manually
        Membership.objects.create(user=self.member_user, chama=self.chama, role="member", status="active")

    def test_create_chama(self):
        self.assertEqual(Chama.objects.count(), 1)

    def test_get_chama_detail(self):
        url = reverse("chama-detail", kwargs={"chama_id": self.chama_id})  # Changed from "pk" to "chama_id"
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Savings Squad")

    def test_add_member_as_admin(self):
        url = reverse("add-member", kwargs={"chama_id": self.chama_id})  # Changed from "groupId" to "chama_id"
        self.client.force_authenticate(user=self.admin_user)
        data = {"email": "out@example.com", "role": "member"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Membership.objects.filter(chama=self.chama).count(), 3)

    def test_add_member_as_non_admin_fails(self):
        url = reverse("add-member", kwargs={"chama_id": self.chama_id})  # Changed from "groupId" to "chama_id"
        self.client.force_authenticate(user=self.member_user)
        data = {"email": "out@example.com"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_members_as_member(self):
        url = reverse("list-members", kwargs={"chama_id": self.chama_id})  # Changed from "groupId" to "chama_id"
        self.client.force_authenticate(user=self.member_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_members_as_non_member_fails(self):
        url = reverse("list-members", kwargs={"chama_id": self.chama_id})  # Changed from "groupId" to "chama_id"
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

# JoinChamaTests 
class JoinChamaTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="test@example.com", phone="0700000004", password="testpass")
        self.chama = Chama.objects.create(
            name="Test Chama",
            currency="KES",
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