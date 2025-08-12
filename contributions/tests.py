from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.utils import timezone
from django.db import transaction
from unittest.mock import patch
from chama.models import Chama, Membership
from users.models import User
from .models import Contribution, ContributionSchedule
from rest_framework_simplejwt.tokens import RefreshToken


class ContributionAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # users
        self.member   = User.objects.create_user(phone='254700000001', email='m@test.com', password='pass')
        self.admin    = User.objects.create_user(phone='254700000002', email='a@test.com', password='pass', is_staff=True)
        self.outsider = User.objects.create_user(phone='254700000003', email='o@test.com', password='pass')

        # chama & schedule
        self.chama    = Chama.objects.create(name='Alpha', currency='KES', minimum_members=1, maximum_members=10)
        self.schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=200
        )

        # memberships
        self.mem_member = Membership.objects.create(user=self.member, chama=self.chama, role=Membership.Role.MEMBER)
        self.mem_admin  = Membership.objects.create(user=self.admin,  chama=self.chama, role=Membership.Role.ADMIN)

        # list URL
        self.list_url = reverse('contributions-list') + f'?chama={self.chama.id}'

    def test_manual_contribution_defaults_to_cash_and_pending(self):
        self.client.force_authenticate(self.member)
        payload = {
            'schedule': str(self.schedule.id),
            'amount':   '200.00'
        }

        resp = self.client.post(self.list_url, payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        contrib = Contribution.objects.get()
        self.assertEqual(contrib.method, Contribution.PaymentMethod.CASH)
        self.assertEqual(contrib.status, Contribution.Status.PENDING)

    def test_cannot_create_mpesa_via_create_endpoint(self):
        self.client.force_authenticate(self.member)
        payload = {
            'schedule': str(self.schedule.id),
            'amount':   '50',
            'method':   'MPESA'
        }
        resp = self.client.post(self.list_url, payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('method', resp.data)

    def test_non_member_forbidden(self):
        self.client.force_authenticate(self.outsider)
        payload = {
            'schedule': str(self.schedule.id),
            'amount':   '100'
        }
        resp = self.client.post(self.list_url, payload)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class ContributionStatusUpdateTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # users
        self.admin_user   = User.objects.create_user(email='adminx@test.com', password='pass', is_staff=True)
        self.regular_user = User.objects.create_user(email='userx@test.com', password='pass')

        # chama & schedule
        self.chama    = Chama.objects.create(name='Beta', currency='KES', minimum_members=1, maximum_members=5)
        self.schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=150
        )

        # memberships & contributions
        self.admin_mem  = Membership.objects.create(user=self.admin_user,   chama=self.chama, role=Membership.Role.ADMIN)
        self.user_mem   = Membership.objects.create(user=self.regular_user, chama=self.chama, role=Membership.Role.MEMBER)
        self.pending    = Contribution.objects.create(
            schedule=self.schedule,
            member=self.user_mem,
            amount=150,
            method=Contribution.PaymentMethod.CASH,
            status=Contribution.Status.PENDING
        )

        self.approved = Contribution.objects.create(
            schedule=self.schedule,
            member=self.user_mem,
            amount=200,
            method=Contribution.PaymentMethod.CASH,
            status=Contribution.Status.APPROVED,
            reference='test-approved-1'
        )

        # auth tokens
        refresh = RefreshToken.for_user(self.admin_user)
        self.admin_token = str(refresh.access_token)

        refresh2 = RefreshToken.for_user(self.regular_user)
        self.user_token = str(refresh2.access_token)

    def get_url(self, contrib_id):
        return reverse('contributions-update-status', kwargs={'pk': contrib_id})

    def authenticate(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_admin_can_approve_and_bump_balance(self):
        initial_balance = self.chama.balance
        self.authenticate(self.admin_token)

        resp = self.client.patch(
            self.get_url(self.pending.id),
            {'status': Contribution.Status.APPROVED},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)

        self.pending.refresh_from_db()
        self.chama.refresh_from_db()
        self.assertEqual(self.pending.status, Contribution.Status.APPROVED)
        self.assertEqual(self.chama.balance, initial_balance + 150)

    def test_admin_can_reject(self):
        self.authenticate(self.admin_token)
        resp = self.client.patch(
            self.get_url(self.pending.id),
            {'status': Contribution.Status.REJECTED},
            format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Contribution.Status.REJECTED)

    def test_invalid_status_value(self):
        self.authenticate(self.admin_token)
        resp = self.client.patch(
            self.get_url(self.pending.id),
            {'status': 'INVALID'},
            format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', resp.data)

    def test_cannot_reupdate_non_pending(self):
        self.authenticate(self.admin_token)
        resp = self.client.patch(
            self.get_url(self.approved.id),
            {'status': Contribution.Status.REJECTED},
            format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_admin_cannot_update(self):
        self.authenticate(self.user_token)
        resp = self.client.patch(
            self.get_url(self.pending.id),
            {'status': Contribution.Status.APPROVED},
            format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class MpesaCallbackTests(APITestCase):
    def setUp(self):
        self.url = '/api/contributions/mpesa-callback/'
        # user & chama
        self.user  = User.objects.create_user(phone='254700000099', email='cb@test.com', password='pass')
        self.chama = Chama.objects.create(name='Gamma', currency='KES', minimum_members=1, maximum_members=8)
        self.schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=300
        )
        Membership.objects.create(user=self.user, chama=self.chama, role=Membership.Role.MEMBER)

    def test_missing_fields_returns_400(self):
        resp = self.client.post(self.url, {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Missing required fields', resp.data['error'])

    def test_unknown_phone_returns_404(self):
        payload = {
            'phone': '254700000000',
            'amount': '100',
            'reference': 'REFX',
            'chama_id': str(self.chama.id),
            'schedule_id': str(self.schedule.id)
        }
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_schedule_or_chama(self):
        payload = {
            'phone':      self.user.phone,
            'amount':     '100',
            'reference':  'REF1',
            'chama_id':   '00000000-0000-0000-0000-000000000000',
            'schedule_id':'00000000-0000-0000-0000-000000000000'
        }
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('schedule_id', resp.data)

    def test_user_not_member_returns_403(self):
        outsider = User.objects.create_user(phone='254700000010', email='x@test.com', password='pass')
        payload = {
            'phone':     outsider.phone,
            'amount':    '100',
            'reference': 'R1',
            'chama_id':  str(self.chama.id),
            'schedule_id': str(self.schedule.id)
        }
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_reference_returns_409(self):
        payload = {
            'phone':     self.user.phone,
            'amount':    '100',
            'reference': 'DUP',
            'chama_id':  str(self.chama.id),
            'schedule_id': str(self.schedule.id)
        }
        # first call
        self.client.post(self.url, payload)
        # duplicate
        resp2 = self.client.post(self.url, payload)
        self.assertEqual(resp2.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(resp2.data['status'], 'DUPLICATE')

    def test_successful_callback_creates_approved_contribution(self):
        initial_balance = self.chama.balance
        payload = {
            'phone':      self.user.phone,
            'amount':     '250',
            'reference':  'OKREF',
            'chama_id':   str(self.chama.id),
            'schedule_id': str(self.schedule.id)
        }
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        contrib = Contribution.objects.get(reference='OKREF')
        self.assertEqual(contrib.method, Contribution.PaymentMethod.MPESA)
        self.assertEqual(contrib.status, Contribution.Status.APPROVED)

        self.chama.refresh_from_db()
        self.assertEqual(self.chama.balance, initial_balance + contrib.amount)

class MpesaInitiationTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # create a user and authenticate
        self.user = User.objects.create_user(
            phone='254700000001',
            email='testuser@example.com',
            password='pass'
        )
        self.client.force_authenticate(user=self.user)

        # create chama and schedule
        self.chama = Chama.objects.create(
            name='TestChama',
            currency='KES',
            minimum_members=1,
            maximum_members=10
        )
        self.schedule = ContributionSchedule.objects.create(
            chama=self.chama,
            due_date=timezone.now().date(),
            expected_amount=100
        )
        Membership.objects.create(
            user=self.user,
            chama=self.chama,
            role=Membership.Role.MEMBER
        )

        # endpoint under test
        self.url = reverse('contributions-initiate-mpesa')

        # patch the Daraja STK Push client
        patcher = patch('contributions.services.mpesa.MpesaDarajaClient.initiate_stk_push')
        self.mock_stk = patcher.start()
        self.addCleanup(patcher.stop)

        # fake a successful Daraja response
        self.mock_stk.return_value = {
            'MerchantRequestID':    '12345',
            'CheckoutRequestID':    'ABCDE',
            'ResponseCode':         '0',
            'ResponseDescription':  'Success'
        }

    def test_initiate_mpesa_success(self):
        """Happy path: valid schedule + member → STK pushed"""
        payload = {
            'schedule': str(self.schedule.id),
            'amount':   '150'
        }
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('CheckoutRequestID', resp.data)
        self.assertIn('reference', resp.data)

        # verify we called Daraja with correct kwargs
        kwargs = self.mock_stk.call_args.kwargs
        self.assertEqual(kwargs['phone_number'], self.user.phone)
        self.assertEqual(kwargs['amount'], '150')
        # reference should contain schedule UUID
        self.assertTrue(kwargs['reference'].startswith(str(self.schedule.id)))
        self.assertIn('/mpesa-callback', kwargs['callback_url'])

    def test_initiate_invalid_schedule(self):
        """Bad schedule ID returns 400 + error key"""
        payload = {
            'schedule': 'not-a-uuid',
            'amount':   '100'
        }
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('schedule', resp.data)

    def test_initiate_non_member_forbidden(self):
        """User not in this chama cannot initiate STK"""
        outsider = User.objects.create_user(
            phone='254700000002',
            email='outsider@example.com',
            password='pass'
        )
        self.client.force_authenticate(user=outsider)

        payload = {
            'schedule': str(self.schedule.id),
            'amount':   '100'
        }
        resp = self.client.post(self.url, payload)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)