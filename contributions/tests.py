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
        self.chama = Chama.objects.create(name='Test Chama', maximum_members=50)
        Membership.objects.create(user=self.member, chama=self.chama, role='member', status='active')
        Membership.objects.create(user=self.admin, chama=self.chama, role='admin', status='active')
        self.client = APIClient()
        self.url = reverse('contributions-list') + f'?chama={self.chama.id}'
        self.root_url = reverse('contributions-list')

    def _create_schedule(self):
        return ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )

    def test_member_can_submit_manual_contribution(self):
        schedule = self._create_schedule()
        self.client.force_authenticate(user=self.member)
        data = {'amount': 100, 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Contribution.objects.filter(member__user=self.member, chama=self.chama).exists())

    def test_non_member_cannot_submit_contribution(self):
        schedule = self._create_schedule()
        self.client.force_authenticate(user=self.non_member)
        data = {'amount': 100, 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_listing_returns_only_own_contributions(self):
        schedule = self._create_schedule()
        Contribution.objects.create(member=self.chama.members.get(user=self.member), chama=self.chama, schedule=schedule, amount=50, method='MPESA')
        Contribution.objects.create(member=self.chama.members.get(user=self.admin), chama=self.chama, schedule=schedule, amount=200, method='BANK')
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data:
            self.assertEqual(item['user'], self.member.id)

    def test_admin_listing_returns_all_contributions(self):
        schedule = self._create_schedule()
        Contribution.objects.create(member=self.chama.members.get(user=self.member), chama=self.chama, schedule=schedule, amount=50, method='MPESA')
        Contribution.objects.create(member=self.chama.members.get(user=self.admin), chama=self.chama, schedule=schedule, amount=200, method='BANK')
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_validation_error_for_invalid_data(self):
        schedule = self._create_schedule()
        self.client.force_authenticate(user=self.member)
        data = {'amount': 'invalid', 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)

    def test_method_not_allowed(self):
        # Permissions run before method-allowed checks; a normal member will be blocked with 403
        self.client.force_authenticate(user=self.member)
        response = self.client.put(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_bypass_member_restrictions(self):
        schedule = self._create_schedule()
        self.client.force_authenticate(user=self.admin)
        data = {'amount': 100, 'method': 'MPESA', 'schedule_id': str(schedule.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Contribution.objects.filter(member__user=self.admin, chama=self.chama).exists())

    def test_root_contributions_requires_admin(self):
        # A plain member (not platform staff and not a chama-admin-of-any-chama) cannot access root
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.root_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_root_contributions_admin_access(self):
        # Platform staff should be able to access root
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.root_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_root_contributions_chama_admin_anychama_access(self):
        # A user who is admin in any chama (but not staff) can access root
        other_admin = User.objects.create_user(email='otheradmin@example.com', password='pass', is_staff=False)
        other_chama = Chama.objects.create(name='Other Chama', maximum_members=20)
        Membership.objects.create(user=other_admin, chama=other_chama, role='admin', status='active')
        self.client.force_authenticate(user=other_admin)
        response = self.client.get(self.root_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_contributions_chama_requires_membership(self):
        other_chama = Chama.objects.create(name='Other', maximum_members=10)
        self.client.force_authenticate(user=self.member)
        url = reverse('contributions-list') + f'?chama={other_chama.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ContributionScheduleAPITests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(email='admin@example.com', password='pass', is_staff=True)
        self.member_user = User.objects.create_user(email='member@example.com', password='pass')
        self.non_member_user = User.objects.create_user(email='outsider@example.com', password='pass')

        self.chama = Chama.objects.create(name='Test Chama', maximum_members=50)
        Membership.objects.create(user=self.admin_user, chama=self.chama, role='admin', status='active')
        Membership.objects.create(user=self.member_user, chama=self.chama, role='member', status='active')

        self.schedule_url = reverse('contribution-schedule-list', kwargs={'chama_id': self.chama.id})

    def test_admin_can_create_schedule(self):
        self.client.force_authenticate(self.admin_user)
        data = {"due_date": timezone.now().date(), "expected_amount": 500}
        response = self.client.post(self.schedule_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_member_cannot_create_schedule(self):
        self.client.force_authenticate(self.member_user)
        data = {"due_date": timezone.now().date(), "expected_amount": 500}
        response = self.client.post(self.schedule_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_member_cannot_access_schedule_list(self):
        self.client.force_authenticate(self.non_member_user)
        response = self.client.get(self.schedule_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_gets_401(self):
        response = self.client.get(self.schedule_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_404_if_chama_does_not_exist(self):
        self.client.force_authenticate(self.admin_user)
        url = reverse('contribution-schedule-list', kwargs={'chama_id': 9999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_update_schedule(self):
        self.client.force_authenticate(self.admin_user)
        schedule = ContributionSchedule.objects.create(chama=self.chama, due_date=timezone.now().date(), expected_amount=100)
        url = reverse('contribution-schedule-detail', kwargs={'chama_id': self.chama.id, 'id': schedule.id})
        response = self.client.patch(url, {"expected_amount": 200})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        schedule.refresh_from_db()
        self.assertEqual(schedule.expected_amount, 200)

    def test_member_cannot_update_schedule(self):
        self.client.force_authenticate(self.member_user)
        schedule = ContributionSchedule.objects.create(chama=self.chama, due_date=timezone.now().date(), expected_amount=100)
        url = reverse('contribution-schedule-detail', kwargs={'chama_id': self.chama.id, 'id': schedule.id})
        response = self.client.patch(url, {"expected_amount": 200})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_schedule(self):
        self.client.force_authenticate(self.admin_user)
        schedule = ContributionSchedule.objects.create(chama=self.chama, due_date=timezone.now().date(), expected_amount=100)
        url = reverse('contribution-schedule-detail', kwargs={'chama_id': self.chama.id, 'id': schedule.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_404_if_schedule_not_in_chama(self):
        self.client.force_authenticate(self.admin_user)
        other_chama = Chama.objects.create(name='Other Chama', maximum_members=20)
        schedule = ContributionSchedule.objects.create(chama=other_chama, due_date=timezone.now().date(), expected_amount=100)
        url = reverse('contribution-schedule-detail', kwargs={'chama_id': self.chama.id, 'id': schedule.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- New tests to ensure 100% coverage of acceptance criteria ---

    def test_chama_in_payload_is_ignored_on_create(self):
        """Ensure the chama in the payload cannot override the path chama_id."""
        other_chama = Chama.objects.create(name='Other Chama', maximum_members=20)
        self.client.force_authenticate(self.admin_user)
        data = {
            "due_date": timezone.now().date(),
            "expected_amount": 250,
            # Attempt to set chama to other_chama in the payload (should be ignored)
            "chama": other_chama.id
        }
        response = self.client.post(self.schedule_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_id = response.data['id']
        sched = ContributionSchedule.objects.get(id=created_id)
        self.assertEqual(sched.chama.id, self.chama.id)  # must be path chama

    def test_create_validation_error_missing_fields(self):
        """Missing required fields should return 400."""
        self.client.force_authenticate(self.admin_user)
        # missing expected_amount
        data = {"due_date": timezone.now().date()}
        response = self.client.post(self.schedule_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('expected_amount', response.data)

    def test_cannot_change_chama_on_update(self):
        """Patching a schedule with a different chama in the payload should not move it."""
        self.client.force_authenticate(self.admin_user)
        schedule = ContributionSchedule.objects.create(chama=self.chama, due_date=timezone.now().date(), expected_amount=100)
        other_chama = Chama.objects.create(name='Other Chama', maximum_members=20)
        url = reverse('contribution-schedule-detail', kwargs={'chama_id': self.chama.id, 'id': schedule.id})
        response = self.client.patch(url, {"chama": other_chama.id, "expected_amount": 150})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        schedule.refresh_from_db()
        self.assertEqual(schedule.chama.id, self.chama.id)
        self.assertEqual(schedule.expected_amount, 150)
