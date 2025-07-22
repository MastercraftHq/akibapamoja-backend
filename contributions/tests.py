from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from chama.models import Chama, Membership
from contributions.models import Contribution, ContributionSchedule

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
        self.url = reverse('contributions-list')  

    def test_member_can_submit_manual_contribution(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        self.client.force_authenticate(user=self.member)
        data = {'amount': 100, 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.url + f'?chama={self.chama.id}', data)
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
        response = self.client.post(self.url + f'?chama={self.chama.id}', data)
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
        response = self.client.get(self.url + f'?chama={self.chama.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data['results']:
            self.assertEqual(item['user'], self.member.id)

    def test_admin_listing_returns_all_contributions(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        Contribution.objects.create(member=self.member_membership, chama=self.chama, schedule=schedule, amount=50, method='MPESA')
        Contribution.objects.create(member=self.admin_membership, chama=self.chama, schedule=schedule, amount=200, method='BANK')
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url + f'?chama={self.chama.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)

    def test_validation_error_for_invalid_data(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        self.client.force_authenticate(user=self.member)
        data = {'amount': 'invalid', 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.url + f'?chama={self.chama.id}', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)

    def test_method_not_allowed(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.put(self.url + f'?chama={self.chama.id}', {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_admin_can_bypass_member_restrictions(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        self.client.force_authenticate(user=self.admin)
        data = {'amount': 100, 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.url + f'?chama={self.chama.id}', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Contribution.objects.filter(member__user=self.admin, chama=self.chama).exists())

    def test_filter_by_chama_id(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        Contribution.objects.create(member=self.member_membership, chama=self.chama, schedule=schedule, amount=50, method='MPESA')
        other_chama = Chama.objects.create(
            name='Other Chama', contribution_amount=100, contribution_day=1, maximum_members=50, contribution_frequency='monthly', currency='KES'
        )
        other_membership = Membership.objects.create(user=self.member, chama=other_chama, role=Membership.Role.MEMBER)
        Contribution.objects.create(member=other_membership, chama=other_chama, schedule=schedule, amount=75, method='BANK')
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.url + f'?chama={self.chama.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['chama'], self.chama.id)

    def test_filter_by_member_id_admin(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        Contribution.objects.create(member=self.member_membership, chama=self.chama, schedule=schedule, amount=50, method='MPESA')
        Contribution.objects.create(member=self.admin_membership, chama=self.chama, schedule=schedule, amount=200, method='BANK')
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url + f'?chama={self.chama.id}&member={self.member_membership.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['member'], self.member_membership.id)
        
    def test_filter_by_member_id_regular_member(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        Contribution.objects.create(member=self.member_membership, chama=self.chama, schedule=schedule, amount=50, method='MPESA')
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.url + f'?chama={self.chama.id}&member={self.member_membership.id}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_combined_filter_chama_and_member_id_admin(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        Contribution.objects.create(member=self.member_membership, chama=self.chama, schedule=schedule, amount=50, method='MPESA')
        Contribution.objects.create(member=self.admin_membership, chama=self.chama, schedule=schedule, amount=200, method='BANK')
        other_chama = Chama.objects.create(
            name='Other Chama', contribution_amount=100, contribution_day=1, maximum_members=50, contribution_frequency='monthly', currency='KES'
        )
        other_membership = Membership.objects.create(user=self.member, chama=other_chama, role=Membership.Role.MEMBER)
        Contribution.objects.create(member=other_membership, chama=other_chama, schedule=schedule, amount=75, method='BANK')
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url + f'?chama={self.chama.id}&member={self.member_membership.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['chama'], self.chama.id)
        self.assertEqual(response.data['results'][0]['member'], self.member_membership.id)  



    def test_invalid_chama_id(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.url + '?chama=999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_member_id(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        Contribution.objects.create(member=self.member_membership, chama=self.chama, schedule=schedule, amount=50, method='MPESA')
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url + f'?chama={self.chama.id}&member=999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pagination_with_filters(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        for _ in range(15):
            Contribution.objects.create(member=self.member_membership, chama=self.chama, schedule=schedule, amount=50, method='MPESA')
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url + f'?chama={self.chama.id}&page_size=10')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIn('next', response.data)