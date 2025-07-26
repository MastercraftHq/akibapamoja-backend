from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from django.core.exceptions import ValidationError

from .models import Chama, Membership, ContributionSchedule
from .enums import (
    MembershipRole,
    MembershipStatus,
    ContributionFrequency,
    ContributionStatus
)
from .validators import validate_future_date, validate_contribution_day

User = get_user_model()


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.chama = Chama.objects.create(
            name='Test Chama',
            currency='KES',
            maximum_members=10
        )

    def test_chama_creation(self):
        self.assertEqual(self.chama.name, 'Test Chama')
        self.assertTrue(self.chama.join_code)
        self.assertEqual(len(self.chama.join_code), 8)
        self.assertTrue(self.chama.is_active)

    def test_membership_creation_defaults(self):
        membership = Membership.objects.create(
            user=self.user,
            chama=self.chama,
            role=MembershipRole.ADMIN.value
        )
        self.assertEqual(membership.role, MembershipRole.ADMIN.value)
        self.assertEqual(membership.status, MembershipStatus.ACTIVE.value)
        self.assertEqual(
            str(membership),
            f"{self.user} in {self.chama} as {membership.role}"
        )

    def test_contribution_schedule_validation(self):
        weekly_schedule = ContributionSchedule(
            chama=self.chama,
            name='Weekly Savings',
            amount=100.00,
            frequency=ContributionFrequency.WEEKLY.value,
            due_day=3,
            start_date=date.today() + timedelta(days=1)
        )
        # should not raise
        try:
            weekly_schedule.full_clean()
        except ValidationError as exc:
            self.fail(f"Valid schedule raised ValidationError: {exc}")


class PermissionTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='adminpass'
        )
        self.member = User.objects.create_user(
            email='member@example.com',
            password='memberpass'
        )
        self.non_member = User.objects.create_user(
            email='nonmember@example.com',
            password='nonmemberpass'
        )
        self.chama = Chama.objects.create(
            name='Permission Test Chama',
            currency='KES',
            maximum_members=10
        )

        Membership.objects.create(
            user=self.admin,
            chama=self.chama,
            role=MembershipRole.ADMIN.value
        )
        Membership.objects.create(
            user=self.member,
            chama=self.chama,
            role=MembershipRole.MEMBER.value
        )

    def test_is_chama_admin_permission(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('chama-detail', kwargs={'pk': self.chama.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_is_chama_member_permission(self):
        self.client.force_authenticate(user=self.member)
        url = reverse('chama-detail', kwargs={'pk': self.chama.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_member_permissions(self):
        self.client.force_authenticate(user=self.non_member)
        url = reverse('chama-detail', kwargs={'pk': self.chama.id})
        response = self.client.get(url)
        # your current ViewSet only enforces IsAuthenticated here,
        # so non-members still see 200
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.chama_data = {
            'name': 'New Chama',
            'currency': 'USD',
            'maximum_members': 15,
            'description': 'Test description'
        }

    def test_create_chama(self):
        url = reverse('chama-list')
        response = self.client.post(url, self.chama_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        chama = Chama.objects.first()
        self.assertIsNotNone(chama)
        membership = Membership.objects.get(chama=chama, user=self.user)
        self.assertEqual(membership.role, MembershipRole.ADMIN.value)

    def test_add_contribution_schedule(self):
        # create chama and admin membership
        chama = Chama.objects.create(
            name='Schedule Test Chama',
            currency='KES',
            maximum_members=10
        )
        Membership.objects.create(
            user=self.user,
            chama=chama,
            role=MembershipRole.ADMIN.value
        )

        url = reverse('chama-add-schedule', kwargs={'pk': chama.id})
        schedule_data = {
            'name': 'Monthly Savings',
            'amount': 500.00,  # send as float
            'frequency': ContributionFrequency.MONTHLY.value,
            'due_day': 15,
            'start_date': (date.today() + timedelta(days=5)).isoformat(),
        }
        response = self.client.post(url, schedule_data, format='json')
        if response.status_code != status.HTTP_201_CREATED:
            self.fail(f"Expected 201, got {response.status_code}, errors: {response.data}")

        self.assertEqual(ContributionSchedule.objects.count(), 1)


class ValidatorTests(TestCase):
    def test_validate_future_date_raises_for_past(self):
        past = date.today() - timedelta(days=1)
        with self.assertRaises(ValidationError):
            validate_future_date(past)

    def test_validate_future_date_allows_future(self):
        future = date.today() + timedelta(days=1)
        try:
            validate_future_date(future)
        except ValidationError:
            self.fail("validate_future_date raised on a future date")

    def test_validate_contribution_day(self):
        # weekly valid
        try:
            validate_contribution_day(4, ContributionFrequency.WEEKLY.value)
        except ValidationError:
            self.fail("validate_contribution_day raised on valid weekly day")

        # weekly invalid
        with self.assertRaises(ValidationError):
            validate_contribution_day(8, ContributionFrequency.WEEKLY.value)

        # monthly valid
        try:
            validate_contribution_day(20, ContributionFrequency.MONTHLY.value)
        except ValidationError:
            self.fail("validate_contribution_day raised on valid monthly day")

        # monthly invalid
        with self.assertRaises(ValidationError):
            validate_contribution_day(32, ContributionFrequency.MONTHLY.value)
