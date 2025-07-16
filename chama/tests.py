from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

from chama.models import Chama, Membership

User = get_user_model()

class ChamaEndpointsTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Create users
        self.admin_user = User.objects.create_user(username="admin", email="admin@example.com", password="adminpass")
        self.member_user = User.objects.create_user(username="member", email="member@example.com", password="memberpass")
        self.other_user = User.objects.create_user(username="outsider", email="out@example.com", password="outpass")

        # Log in admin user and create Chama
        self.client.force_authenticate(user=self.admin_user)
        self.create_chama_url = reverse("create-chama")
        self.chama_data = {
            "name": "Savings Squad",
            "description": "Monthly savings group",
            "contribution_amount": "1000.00",
            "contribution_frequency": "monthly",
            "contribution_day": 5,
            "currency": "KES",
            "late_payment_fee": "100.00",
            "minimum_members": 1,
            "maximum_members": 10,
            "join_code": "JOIN1234"
        }
        response = self.client.post(self.create_chama_url, self.chama_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.chama = Chama.objects.first()
        self.group_id = self.chama.id

        # Add admin membership (created automatically on POST /groups)
        self.admin_membership = Membership.objects.get(user=self.admin_user, chama=self.chama)

        # Add member manually
        Membership.objects.create(user=self.member_user, chama=self.chama, role="member", status="active")

    def test_create_chama(self):
        self.assertEqual(Chama.objects.count(), 1)

    def test_get_chama_detail(self):
        url = reverse("chama-detail", kwargs={"pk": self.group_id})
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Savings Squad")

    def test_add_member_as_admin(self):
        url = reverse("add-member", kwargs={"groupId": self.group_id})
        self.client.force_authenticate(user=self.admin_user)
        data = {"email": "out@example.com", "role": "member"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Membership.objects.filter(chama=self.chama).count(), 3)

    def test_add_member_as_non_admin_fails(self):
        url = reverse("add-member", kwargs={"groupId": self.group_id})
        self.client.force_authenticate(user=self.member_user)
        data = {"email": "out@example.com"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
