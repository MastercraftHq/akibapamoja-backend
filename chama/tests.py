# chama/tests.py
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Chama, Membership

User = get_user_model()


class ChamaAPITest(APITestCase):
    def setUp(self):
        # Adapt to your custom create_user signature (email & phone required)
        self.user_admin = User.objects.create_user(
            email='admin@example.com',
            phone='+254700000001',
            password='pass'
        )
        self.user_other = User.objects.create_user(
            email='other@example.com',
            phone='+254700000002',
            password='pass'
        )

        self.client_admin = APIClient()
        self.client_admin.force_authenticate(user=self.user_admin)

        self.client_other = APIClient()
        self.client_other.force_authenticate(user=self.user_other)

    def test_create_chama_auto_join_code_and_admin_membership(self):
        url = reverse('create-chama')
        data = {
            'name': 'TestChama',
            'currency': 'KES',
            'maximum_members': 5
        }
        response = self.client_admin.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        chama_id = response.data['id']
        self.assertIn('join_code', response.data)
        self.assertEqual(len(response.data['join_code']), 8)

        membership = Membership.objects.get(
            user=self.user_admin,
            chama_id=chama_id
        )
        self.assertEqual(membership.role, Membership.Role.ADMIN)
        self.assertEqual(membership.status, Membership.Status.ACTIVE)

    def test_retrieve_chama_detail(self):
        chama = Chama.objects.create(
            name='DuoChama',
            currency='USD',
            maximum_members=10
        )
        url = reverse('chama-detail', kwargs={'pk': chama.id})
        response = self.client_admin.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'DuoChama')

    def test_add_member_by_admin(self):
        chama = Chama.objects.create(
            name='Alpha',
            currency='EUR',
            maximum_members=3
        )
        Membership.objects.create(
            user=self.user_admin,
            chama=chama,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE
        )

        url = reverse('add-member', kwargs={'groupId': chama.id})
        data = {'email': self.user_other.email, 'role': Membership.Role.MEMBER}
        response = self.client_admin.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        m = Membership.objects.get(user=self.user_other, chama=chama)
        self.assertEqual(m.status, Membership.Status.INVITED)

    def test_add_member_by_non_admin_forbidden(self):
        chama = Chama.objects.create(
            name='Beta',
            currency='GBP',
            maximum_members=4
        )
        Membership.objects.create(
            user=self.user_admin,
            chama=chama,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE
        )

        url = reverse('add-member', kwargs={'groupId': chama.id})
        data = {'email': self.user_other.email}
        response = self.client_other.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_members_by_active_member(self):
        chama = Chama.objects.create(
            name='Gamma',
            currency='JPY',
            maximum_members=6
        )
        Membership.objects.create(
            user=self.user_admin,
            chama=chama,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE
        )
        Membership.objects.create(
            user=self.user_other,
            chama=chama,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE
        )

        url = reverse('list-members', kwargs={'groupId': chama.id})
        response = self.client_other.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_join_chama_and_duplicate(self):
        chama = Chama.objects.create(
            name='Delta',
            currency='AUD',
            maximum_members=8
        )
        Membership.objects.create(
            user=self.user_admin,
            chama=chama,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE
        )
        code = chama.join_code

        url = reverse('join-chama')
        response1 = self.client_other.post(
            url, {'join_code': code}, format='json'
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        m1 = Membership.objects.get(user=self.user_other, chama=chama)
        self.assertEqual(m1.status, Membership.Status.PENDING)

        response2 = self.client_other.post(
            url, {'join_code': code}, format='json'
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('You are already a member', str(response2.data))
