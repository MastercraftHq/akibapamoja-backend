from django.urls import reverse
from datetime import date
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from chama.models import Chama, Membership
from contributions.models import Contribution, ContributionSchedule
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class ContributionAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.member = User.objects.create_user(email='member@example.com', password='pass')
        self.admin = User.objects.create_user(email='admin@example.com', password='pass', is_staff=True)
        self.non_member = User.objects.create_user(email='outsider@example.com', password='pass')

        self.chama = Chama.objects.create(
            name='Test Chama',
            contribution_amount=100,
            contribution_day=1,
            maximum_members=50
        )

        self.member_membership = Membership.objects.create(user=self.member, chama=self.chama)
        self.admin_membership = Membership.objects.create(user=self.admin, chama=self.chama)

        self.schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )

        self.url = reverse('contributions-list') + f'?chama={self.chama.id}'

    def test_member_can_submit_manual_contribution(self):
        self.client.force_authenticate(user=self.member)
        data = {'amount': 100, 'method': 'CASH', 'schedule': str(self.schedule.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        contribution = Contribution.objects.get()
        self.assertEqual(contribution.status, 'PENDING')
        self.assertEqual(contribution.method, 'CASH')

    def test_mpesa_contribution_auto_approved(self):
        self.client.force_authenticate(user=self.member)
        data = {
            'amount': 100, 
            'method': 'MPESA', 
            'schedule': str(self.schedule.id),
            'reference': 'MPESA12345'  # Add required reference
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        contribution = Contribution.objects.get()
        self.assertEqual(contribution.status, 'APPROVED')
        self.assertEqual(contribution.method, 'MPESA')

    def test_duplicate_mpesa_contribution_is_rejected(self):
        self.client.force_authenticate(user=self.member)
        Contribution.objects.create(
            member=self.member_membership,
            chama=self.chama,
            schedule=self.schedule,
            amount=100,
            method='MPESA',
            status='APPROVED',
            reference='MPESA12345'
        )
        data = {
            'amount': 100, 
            'method': 'MPESA', 
            'schedule': str(self.schedule.id),
            'reference': 'MPESA12345'  # Same reference
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_member_cannot_contribute(self):
        self.client.force_authenticate(user=self.non_member)
        data = {'amount': 100, 'method': 'CASH', 'schedule': str(self.schedule.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_only_list_own_contributions(self):
        Contribution.objects.create(
            member=self.member_membership, chama=self.chama, schedule=self.schedule,
            amount=50, method='MPESA', status='APPROVED'
        )
        Contribution.objects.create(
            member=self.admin_membership, chama=self.chama, schedule=self.schedule,
            amount=200, method='BANK', status='APPROVED'
        )
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all([item['user'] == self.member.id for item in response.data]))

    def test_admin_can_see_all_contributions(self):
        Contribution.objects.create(
            member=self.member_membership, chama=self.chama, schedule=self.schedule,
            amount=50, method='MPESA', status='APPROVED'
        )
        Contribution.objects.create(
            member=self.admin_membership, chama=self.chama, schedule=self.schedule,
            amount=200, method='BANK', status='APPROVED'
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.url)
        self.assertEqual(len(response.data), 2)

    def test_invalid_data_validation(self):
        self.client.force_authenticate(user=self.member)
        data = {'amount': 'invalid', 'method': 'CASH', 'schedule': str(self.schedule.id)}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)

    def test_method_not_allowed(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.put(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ContributionStatusUpdateTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(email='admin@example.com', password='adminpass', is_staff=True)
        self.regular_user = User.objects.create_user(email='regular@example.com', password='regularpass')

        self.chama = Chama.objects.create(
            name="Test Chama",
            contribution_amount=100.00,
            contribution_frequency="monthly",
            contribution_day=21,
            currency="KES",
            maximum_members=10,
        )
        self.admin_membership = Membership.objects.create(user=self.admin_user, chama=self.chama, role=Membership.Role.ADMIN)
        self.regular_membership = Membership.objects.create(user=self.regular_user, chama=self.chama, role=Membership.Role.MEMBER)

        self.schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )

        self.pending_contribution = Contribution.objects.create(
            member=self.regular_membership,
            chama=self.chama,
            schedule=self.schedule,
            amount=100.00,
            status='PENDING'
        )

        self.approved_contribution = Contribution.objects.create(
            member=self.regular_membership,
            chama=self.chama,
            schedule=self.schedule,
            amount=150.00,
            status='APPROVED'
        )

        self.admin_token = self.get_token(self.admin_user)
        self.user_token = self.get_token(self.regular_user)

    def get_token(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def authenticate(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def get_update_url(self, contribution_id):
        return reverse('contributions-update-status', kwargs={'pk': contribution_id})

    def test_admin_can_approve_pending_contribution(self):
        self.authenticate(self.admin_token)
        res = self.client.patch(
            self.get_update_url(self.pending_contribution.id),
            {"status": "APPROVED"},
            format='json'
        )
        self.assertEqual(res.status_code, 200)
        self.pending_contribution.refresh_from_db()
        self.assertEqual(self.pending_contribution.status, "APPROVED")

    def test_admin_can_reject_pending_contribution(self):
        self.authenticate(self.admin_token)
        res = self.client.patch(
            self.get_update_url(self.pending_contribution.id),
            {"status": "REJECTED"},  # Now matches model
            format='json'
        )
        self.assertEqual(res.status_code, 200)
        self.pending_contribution.refresh_from_db()
        self.assertEqual(self.pending_contribution.status, "REJECTED")

    def test_invalid_status_is_rejected(self):
        self.authenticate(self.admin_token)
        res = self.client.patch(
            self.get_update_url(self.pending_contribution.id),
            {"status": "INVALID"},
            format='json'
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn('status', res.data)

    def test_only_pending_can_be_updated(self):
        self.authenticate(self.admin_token)
        res = self.client.patch(
            self.get_update_url(self.approved_contribution.id),
            {"status": "REJECTED"},
            format='json'
        )
        self.assertEqual(res.status_code, 400)

    def test_non_admin_cannot_update(self):
        self.authenticate(self.user_token)
        res = self.client.patch(
            self.get_update_url(self.pending_contribution.id),
            {"status": "APPROVED"},
            format='json'
        )
        self.assertEqual(res.status_code, 403)

    def test_admin_cannot_update_other_chama_contribution(self):
        other_chama = Chama.objects.create(
            name="Other Chama",
            contribution_amount=200,
            contribution_frequency="monthly",
            contribution_day=15,
            currency="KES",
            maximum_members=10
        )
        other_member = Membership.objects.create(
            user=self.regular_user, chama=other_chama, role=Membership.Role.MEMBER
        )
        other_schedule = ContributionSchedule.objects.create(
            chama=other_chama,
            due_date=timezone.now().date(),
            expected_amount=200
        )
        other_contribution = Contribution.objects.create(
            member=other_member,
            chama=other_chama,
            schedule=other_schedule,
            amount=200,
            status='PENDING'
        )
        self.authenticate(self.admin_token)
        res = self.client.patch(
            self.get_update_url(other_contribution.id),
            {"status": "APPROVED"},
            format='json'
        )
        self.assertEqual(res.status_code, 403)

    def test_db_reflects_status_update(self):
        self.authenticate(self.admin_token)
        self.client.patch(
            self.get_update_url(self.pending_contribution.id),
            {"status": "APPROVED"},
            format='json'
        )
        updated = Contribution.objects.get(pk=self.pending_contribution.id)
        self.assertEqual(updated.status, "APPROVED")
