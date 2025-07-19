# contributions/tests.py
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from chama.models import Chama, Membership
from .models import Contribution, ActivityLog
from django.contrib.auth import get_user_model

User = get_user_model()

class ContributionEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='user1', email='user1@example.com', password='testpass', role='user'
        )
        self.admin = User.objects.create_user(
            username='admin', email='admin@example.com', password='testpass', role='Admin'
        )
        self.treasurer = User.objects.create_user(
            username='treasurer', email='treasurer@example.com', password='testpass', role='Treasure'
        )
        self.member3 = User.objects.create_user(
            username='member3', email='member3@example.com', password='testpass', role='user'
        )
        self.chama = Chama.objects.create(
            name='Test Chama',
            contribution_amount=100.00,
            contribution_frequency='monthly',
            contribution_day=1,
            currency='USD',
            maximum_members=10,
            balance=0
        )
        self.membership_user = Membership.objects.create(
            user=self.user1, chama=self.chama, role='member', status='active'
        )
        self.membership_admin = Membership.objects.create(
            user=self.admin, chama=self.chama, role='admin', status='active'
        )
        self.membership_treasurer = Membership.objects.create(
            user=self.treasurer, chama=self.chama, role='treasurer', status='active'
        )
        self.membership_member3 = Membership.objects.create(
            user=self.member3, chama=self.chama, role='member', status='active'
        )
        self.contribution1 = Contribution.objects.create(
            user=self.user1, chama=self.chama, amount=100.00, method='MPESA', status='SUCCESS'
        )
        self.contribution2 = Contribution.objects.create(
            user=self.admin, chama=self.chama, amount=200.00, method='BANK', status='SUCCESS'
        )
        self.contribution3 = Contribution.objects.create(
            user=self.member3, chama=self.chama, amount=150.00, method='MPESA', status='SUCCESS'
        )
        for i in range(15):
            Contribution.objects.create(
                user=self.user1, chama=self.chama, amount=50.00, method='MPESA', status='SUCCESS'
            )

    def test_filter_by_chama_id(self):
        self.client.login(username='user1', password='testpass')
        response = self.client.get(
            reverse('contributions:list-contributions') + f'?chama_id={self.chama.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertEqual(float(response.data['results'][0]['amount']), 100.00)

    def test_admin_filter_by_member_id(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(
            reverse('contributions:list-contributions') + f'?chama_id={self.chama.id}&member_id={self.member3.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(float(response.data['results'][0]['amount']), 150.00)

    def test_treasurer_filter_by_member_id(self):
        self.client.login(username='treasurer', password='testpass')
        response = self.client.get(
            reverse('contributions:list-contributions') + f'?chama_id={self.chama.id}&member_id={self.member3.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(float(response.data['results'][0]['amount']), 150.00)

    def test_regular_member_cannot_filter_by_member_id(self):
        self.client.login(username='user1', password='testpass')
        response = self.client.get(
            reverse('contributions:list-contributions') + f'?chama_id={self.chama.id}&member_id={self.member3.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_id_without_chama_id(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(
            reverse('contributions:list-contributions') + f'?member_id={self.member3.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_chama_id(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(
            reverse('contributions:list-contributions') + f'?chama_id=999&member_id={self.member3.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthorized_access(self):
        response = self.client.get(reverse('contributions:list-contributions'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_combined_filtering(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(
            reverse('contributions:list-contributions') + f'?chama_id={self.chama.id}&member_id={self.member3.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(float(response.data['results'][0]['amount']), 150.00)

    def test_pagination(self):
        self.client.login(username='admin', password='testpass')
        response = self.client.get(
            reverse('contributions:list-contributions') + f'?chama_id={self.chama.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertTrue('next' in response.data)