from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from chama.models import Chama, Membership
from .models import Contribution, ContributionSchedule

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
        Contribution.objects.create(member=self.chama.members.get(user=self.member), chama=self.chama, schedule=schedule, amount=50, method='MPESA')
        Contribution.objects.create(member=self.chama.members.get(user=self.admin), chama=self.chama, schedule=schedule, amount=200, method='BANK')
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data:
            self.assertEqual(item['user'], self.member.id)

    def test_admin_listing_returns_all_contributions(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        Contribution.objects.create(member=self.chama.members.get(user=self.member), chama=self.chama, schedule=schedule, amount=50, method='MPESA')
        Contribution.objects.create(member=self.chama.members.get(user=self.admin), chama=self.chama, schedule=schedule, amount=200, method='BANK')
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

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

    def test_admin_can_successfully_edit_contribution(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        contribution = Contribution.objects.create(
            member=self.chama.members.get(user=self.member), 
            chama=self.chama, 
            schedule=schedule, 
            amount=50, 
            method='MPESA'
        )
        self.client.force_authenticate(user=self.admin)
        update_url = reverse('contributions-detail', kwargs={'pk': contribution.id}) + f'?chama={self.chama.id}'
        data = {'amount': 75, 'notes': 'Updated by admin'}
        response = self.client.patch(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        contribution.refresh_from_db()
        self.assertEqual(contribution.amount, 75)
        self.assertEqual(contribution.notes, 'Updated by admin')

    def test_admin_can_successfully_delete_any_contribution(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        contribution = Contribution.objects.create(
            member=self.chama.members.get(user=self.member), 
            chama=self.chama, 
            schedule=schedule, 
            amount=50, 
            method='MPESA'
        )
        self.client.force_authenticate(user=self.admin)
        delete_url = reverse('contributions-detail', kwargs={'pk': contribution.id}) + f'?chama={self.chama.id}'
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Contribution.objects.filter(id=contribution.id).exists())

    def test_member_cannot_edit_any_contribution(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        contribution = Contribution.objects.create(
            member=self.chama.members.get(user=self.member), 
            chama=self.chama, 
            schedule=schedule, 
            amount=50, 
            method='MPESA'
        )
        self.client.force_authenticate(user=self.member)
        update_url = reverse('contributions-detail', kwargs={'pk': contribution.id}) + f'?chama={self.chama.id}'
        data = {'amount': 75}
        response = self.client.patch(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_delete_own_pending_contribution(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        contribution = Contribution.objects.create(
            member=self.chama.members.get(user=self.member), 
            chama=self.chama, 
            schedule=schedule, 
            amount=50, 
            method='MPESA',
            status='PENDING'
        )
        self.client.force_authenticate(user=self.member)
        delete_url = reverse('contributions-detail', kwargs={'pk': contribution.id}) + f'?chama={self.chama.id}'
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Contribution.objects.filter(id=contribution.id).exists())

    def test_member_cannot_delete_non_pending_contribution(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        contribution = Contribution.objects.create(
            member=self.chama.members.get(user=self.member), 
            chama=self.chama, 
            schedule=schedule, 
            amount=50, 
            method='MPESA',
            status='APPROVED'
        )
        self.client.force_authenticate(user=self.member)
        delete_url = reverse('contributions-detail', kwargs={'pk': contribution.id}) + f'?chama={self.chama.id}'
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Contribution.objects.filter(id=contribution.id).exists())

    def test_unauthenticated_user_forbidden_from_edit_endpoint(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        contribution = Contribution.objects.create(
            member=self.chama.members.get(user=self.member), 
            chama=self.chama, 
            schedule=schedule, 
            amount=50, 
            method='MPESA'
        )
        update_url = reverse('contributions-detail', kwargs={'pk': contribution.id}) + f'?chama={self.chama.id}'
        data = {'amount': 75}
        response = self.client.patch(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_user_forbidden_from_delete_endpoint(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        contribution = Contribution.objects.create(
            member=self.chama.members.get(user=self.member), 
            chama=self.chama, 
            schedule=schedule, 
            amount=50, 
            method='MPESA'
        )
        delete_url = reverse('contributions-detail', kwargs={'pk': contribution.id}) + f'?chama={self.chama.id}'
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_fields_in_update_trigger_validation_errors(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        contribution = Contribution.objects.create(
            member=self.chama.members.get(user=self.member), 
            chama=self.chama, 
            schedule=schedule, 
            amount=50, 
            method='MPESA'
        )
        self.client.force_authenticate(user=self.admin)
        update_url = reverse('contributions-detail', kwargs={'pk': contribution.id}) + f'?chama={self.chama.id}'
        data = {'amount': 75, 'method': 'BANK', 'invalid_field': 'should_not_be_allowed'}
        response = self.client.patch(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('invalid_field', str(response.data['error']))

    def test_contribution_not_found_returns_404(self):
        self.client.force_authenticate(user=self.admin)
        update_url = reverse('contributions-detail', kwargs={'pk': 99999}) + f'?chama={self.chama.id}'
        data = {'amount': 75}
        response = self.client.patch(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthorized_access_returns_403(self):
        schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        contribution = Contribution.objects.create(
            member=self.chama.members.get(user=self.member), 
            chama=self.chama, 
            schedule=schedule, 
            amount=50, 
            method='MPESA'
        )
        self.client.force_authenticate(user=self.non_member)
        update_url = reverse('contributions-detail', kwargs={'pk': contribution.id}) + f'?chama={self.chama.id}'
        data = {'amount': 75}
        response = self.client.patch(update_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

