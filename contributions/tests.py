from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from chama.models import Chama, Membership
from .models import Contribution

User = get_user_model()

class ContributionAPITests(APITestCase):
    def setUp(self):
        self.member = User.objects.create_user(
            username='member', password='pass', email=f'member_{self._testMethodName}@example.com'
        )
        self.admin = User.objects.create_user(
            username='admin', password='pass', is_staff=True, email=f'admin_{self._testMethodName}@example.com'
        )
        self.non_member = User.objects.create_user(
            username='outsider', password='pass', email=f'outsider_{self._testMethodName}@example.com'
        )
        self.chama = Chama.objects.create(name='Test Chama', contribution_amount=100, contribution_day=1)
        Membership.objects.create(user=self.member, chama=self.chama)
        Membership.objects.create(user=self.admin, chama=self.chama)
        self.client = APIClient()
        self.url = reverse('contribution-list') + f'?chama={self.chama.id}'

    def test_member_can_submit_manual_contribution(self):
        self.client.force_authenticate(user=self.member)
        data = {'amount': 100, 'method': 'MPESA'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Contribution.objects.filter(user=self.member, chama=self.chama).exists())

    def test_non_member_cannot_submit_contribution(self):
        self.client.force_authenticate(user=self.non_member)
        data = {'amount': 100, 'method': 'MPESA'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_listing_returns_only_own_contributions(self):
        Contribution.objects.create(user=self.member, chama=self.chama, amount=50, method='MPESA')
        Contribution.objects.create(user=self.admin, chama=self.chama, amount=200, method='BANK')
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data:
            self.assertEqual(item['user'], self.member.id)

    def test_admin_listing_returns_all_contributions(self):
        Contribution.objects.create(user=self.member, chama=self.chama, amount=50, method='MPESA')
        Contribution.objects.create(user=self.admin, chama=self.chama, amount=200, method='BANK')
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_validation_error_for_invalid_data(self):
        self.client.force_authenticate(user=self.member)
        data = {'amount': 'invalid', 'method': 'MPESA'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)

    def test_method_not_allowed(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.put(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_admin_can_bypass_member_restrictions(self):
        self.client.force_authenticate(user=self.admin)
        data = {'amount': 100, 'method': 'MPESA'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Contribution.objects.filter(user=self.admin, chama=self.chama).exists())
