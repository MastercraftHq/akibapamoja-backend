from django.urls import reverse
from datetime import date
from rest_framework.test import APITestCase, APIClient
from django.test import TestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from chama.models import Chama, Membership
from .models import Contribution, ContributionSchedule
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import RefreshToken

import uuid

User = get_user_model()

class ContributionAPITests(APITestCase):
    def setUp(self):
        self.member = User.objects.create_user(
            password='pass', email=f'member_{self._testMethodName}@example.com'
        )
        self.admin = User.objects.create_user(
            password='pass', is_staff=True, email=f'admin_{self._testMethodName}@example.com'
        )
        self.non_member = User.objects.create_user(
            password='pass', email=f'outsider_{self._testMethodName}@example.com'
        )
        self.chama = Chama.objects.create(name='Test Chama', contribution_amount=100, contribution_day=1, maximum_members=50)
        Membership.objects.create(user=self.member, chama=self.chama)
        Membership.objects.create(user=self.admin, chama=self.chama)
        self.client = APIClient()
        self.url = reverse('contributions-list') + f'?chama={self.chama.id}'

    def test_member_can_submit_manual_contribution(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        self.client.force_authenticate(user=self.member)
        data = {'amount': 100, 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Contribution.objects.filter(member__user=self.member, chama=self.chama).exists())

    def test_non_member_cannot_submit_contribution(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        self.client.force_authenticate(user=self.non_member)
        data = {'amount': 100, 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_listing_returns_only_own_contributions(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        Contribution.objects.create(member=self.chama.members.get(user=self.member), chama=self.chama, schedule=schedule, amount=50, method='MPESA', status='APPROVED')
        Contribution.objects.create(member=self.chama.members.get(user=self.admin), chama=self.chama, schedule=schedule, amount=200, method='BANK', status='APPROVED')
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user'], self.member.id)

    def test_admin_listing_returns_all_contributions(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        Contribution.objects.create(member=self.chama.members.get(user=self.member), chama=self.chama, schedule=schedule, amount=50, method='MPESA', status='APPROVED')
        Contribution.objects.create(member=self.chama.members.get(user=self.admin), chama=self.chama, schedule=schedule, amount=200, method='BANK', status='APPROVED')
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_validation_error_for_invalid_data(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        self.client.force_authenticate(user=self.member)
        data = {'amount': 'invalid', 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)

    def test_method_not_allowed(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.put(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_admin_can_bypass_member_restrictions(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        self.client.force_authenticate(user=self.admin)
        data = {'amount': 100, 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Contribution.objects.filter(member__user=self.admin, chama=self.chama).exists())

class ContributionStatusUpdateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()

        # Create users
        self.admin_user = User.objects.create_user(
            username='admin', email='admin@example.com', password='adminpass'
        )
        self.other_user = User.objects.create_user(
            username='other', email='other@example.com', password='otherpass'
        )

        # Create chamas
        self.chama1 = Chama.objects.create(
            name="Chama 1",
            contribution_amount=100.00,
            contribution_frequency="monthly",
            contribution_day=21,
            currency="KES",
            maximum_members=10,
        )
        self.chama2 = Chama.objects.create(
            name="Chama 2",
            contribution_amount=100.00,
            contribution_frequency="monthly",
            contribution_day=21,
            currency="KES",
            maximum_members=10,
        )

        # Assign admin role to admin_user in chama1
        Membership.objects.create(
            user=self.admin_user, chama=self.chama1, role=Membership.Role.ADMIN
        )

        # Contributions
        self.contribution1 = Contribution.objects.create(
            chama=self.chama1, amount=100.00, status='pending'
        )
        self.contribution2 = Contribution.objects.create(
            chama=self.chama2, amount=100.00, status='pending'
        )

        # JWT token for admin_user
        self.admin_token = self.get_token_for_user(self.admin_user)

    def get_token_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_admin_can_update_own_chama_contribution_status(self):
        """Admin should be able to approve a contribution in their own chama."""
        url = f"/api/contributions/{self.contribution1.id}/update-status/"
        data = {"status": "approved"}

        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.admin_token)
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("status"), "approved")

        self.contribution1.refresh_from_db()
        self.assertEqual(self.contribution1.status, "approved")

    def test_admin_cannot_update_other_chama_contribution_status(self):
        """Admin should not be able to update contributions in a chama they don't admin."""
        url = f"/api/contributions/{self.contribution2.id}/update-status/"
        data = {"status": "approved"}

        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.admin_token)
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, 403)