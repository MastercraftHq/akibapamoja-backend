# contributions/tests.py
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from chama.models import Chama, Membership
from contributions.models import Contribution, ContributionSchedule
from decimal import Decimal 

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
        self.chama = Chama.objects.create(
            name='Test Chama',
            description='Test Chama Description',
            currency='KES',
            minimum_members=1,
            maximum_members=50,
            balance=0,
            is_active=True,
            join_code='TEST1234',
            contribution_amount=Decimal('100.00'),  
            contribution_frequency="monthly",  
            contribution_day=5  
        )
        self.member_membership = Membership.objects.create(
            user=self.member,
            chama=self.chama,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE
        )
        self.admin_membership = Membership.objects.create(
            user=self.admin,
            chama=self.chama,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE
        )
        self.client = APIClient()

    def get_contributions_url(self, chama_id):
        return reverse('contributions-list', kwargs={'chama_id': chama_id})

    def test_member_can_submit_manual_contribution(self):
        """
        Sets up a ContributionSchedule instance to define the expected contribution
        parameters (amount and due date) for the Chama group. This replaces legacy
        logic from the Chama model, allowing dynamic control over contributions.
        """
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        self.client.force_authenticate(user=self.member)
        data = {'amount': 100, 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.get_contributions_url(self.chama.id), data)
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
        response = self.client.post(self.get_contributions_url(self.chama.id), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_listing_returns_only_own_contributions(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        Contribution.objects.create(member=self.member_membership, chama=self.chama, schedule=schedule, amount=50, method='MPESA')
        Contribution.objects.create(member=self.admin_membership, chama=self.chama, schedule=schedule, amount=200, method='BANK')
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.get_contributions_url(self.chama.id))
        data = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        for item in data:
            self.assertEqual(item['member'], self.member_membership.id)

    def test_admin_listing_returns_all_contributions(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        Contribution.objects.create(member=self.member_membership, chama=self.chama, schedule=schedule, amount=50, method='MPESA')
        Contribution.objects.create(member=self.admin_membership, chama=self.chama, schedule=schedule, amount=200, method='BANK')
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.get_contributions_url(self.chama.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data

    def test_validation_error_for_invalid_data(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        self.client.force_authenticate(user=self.member)
        data = {'amount': 'invalid', 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.get_contributions_url(self.chama.id), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)

    def test_method_not_allowed(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.put(self.get_contributions_url(self.chama.id), {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_admin_can_bypass_member_restrictions(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        self.client.force_authenticate(user=self.admin)
        data = {'amount': 100, 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.get_contributions_url(self.chama.id), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Contribution.objects.filter(member__user=self.admin, chama=self.chama).exists())