from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction

from .models import Contribution, ActivityLog, ContributionSchedule
from chama.models import Chama, Membership
from .serializers import (
    ContributionSerializer,
    ContributionCreateSerializer,
    ContributionScheduleSerializer,
)
from .permissions import IsChamaMemberOrAdminWrite, IsChamaAdminOrReadOnly
from .utils import get_user_by_phone, get_chama_for_user


class ContributionViewSet(viewsets.ModelViewSet):
    """
    Contributions endpoint behavior:
    - GET /api/contributions/                 -> platform staff OR chama-admin-of-any-chama
    - GET /api/contributions/?chama=<id>      -> platform staff OR members of that chama
    - POST /api/contributions/?chama=<id>     -> active members (creates contribution)
    - Other unsafe methods on contributions    -> require chama admin (handled by permission class)
    """
    serializer_class = ContributionSerializer
    permission_classes = [permissions.IsAuthenticated, IsChamaMemberOrAdminWrite]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']

    def _user_is_admin_in_any_chama(self, user):
        return Membership.objects.filter(user=user, role__iexact='admin', status__iexact='active').exists()

    def get_queryset(self):
        user = self.request.user
        chama_id = self.request.query_params.get('chama')

        # Root endpoint: /contributions/  (no ?chama=)
        if not chama_id:
            # allow platform staff OR chama-admin-of-any-chama
            if not (getattr(user, "is_staff", False) or self._user_is_admin_in_any_chama(user)):
                raise PermissionDenied("Only platform staff or chama-admins can access this endpoint.")
            return Contribution.objects.all().select_related('member__user', 'schedule').order_by('-transaction_date')

        # chama-specific: validate chama exists (404 if not)
        # <- get_object_or_404 will raise Http404 which DRF turns into a 404 response
        chama = get_object_or_404(Chama, id=chama_id)

        # Check membership
        is_member = Membership.objects.filter(user=user, chama=chama).exists()
        if not (getattr(user, "is_staff", False) or is_member):
            raise PermissionDenied("You are not authorized to view contributions for this Chama.")

        # If platform staff or chama-admin -> see all contributions for the chama
        is_chama_admin = Membership.objects.filter(
            user=user, chama=chama, role__iexact='admin', status__iexact='active'
        ).exists()

        if getattr(user, "is_staff", False) or is_chama_admin:
            return Contribution.objects.filter(
                chama=chama
            ).select_related('member__user', 'schedule').order_by('-transaction_date')

        # Otherwise (regular member) — only their own contributions
        return Contribution.objects.filter(
            chama=chama,
            member__user=user
        ).select_related('schedule').order_by('-transaction_date')

    def get_serializer_class(self):
        if self.action == 'create':
            return ContributionCreateSerializer
        return ContributionSerializer

    def get_serializer_context(self):
        """
        Provide chama object when ?chama= is present. If no chama param and user is platform staff
        or chama-admin-in-any-chama, allow access but set chama=None. Otherwise raise PermissionDenied.
        """
        context = super().get_serializer_context()
        chama_id = self.request.query_params.get('chama')

        if not chama_id:
            # If no chama_id and user is not platform staff nor chama-admin-of-any-chama, block
            if not (getattr(self.request.user, "is_staff", False) or self._user_is_admin_in_any_chama(self.request.user)):
                raise PermissionDenied("Only platform staff or chama-admins can access this endpoint.")
            context['chama'] = None
            return context

        # ensure 404 if chama doesn't exist
        context['chama'] = get_object_or_404(Chama, id=chama_id)
        return context

    def perform_create(self, serializer):
        chama = self.get_serializer_context().get('chama')
        if not chama:
            # This is defensive — get_serializer_context already raises if chama_id invalid
            raise NotFound("Chama not found.")

        # Ensure user is a member of the chama
        if not Membership.objects.filter(user=self.request.user, chama=chama).exists():
            raise PermissionDenied("You are not a member of this Chama.")

        contribution = serializer.save(chama=chama, status='SUCCESS')

        # Update chama balance
        chama.balance += contribution.amount
        chama.save()

        # Log the activity
        ActivityLog.objects.create(
            user=self.request.user,
            chama=chama,
            action='CONTRIBUTION',
            details=f"Manual contribution of KES {serializer.validated_data.get('amount', contribution.amount):.2f}"
        )


@csrf_exempt
@api_view(['POST'])
@permission_classes([])
def mpesa_callback(request):
    """Handle M-Pesa STK push callback."""
    data = request.data
    try:
        callback = data.get('Body', {}).get('stkCallback', {})
        metadata_items = callback.get('CallbackMetadata', {}).get('Item', [])

        # Extract amount, receipt and phone
        amount_item = next((i for i in metadata_items if i.get('Name') == 'Amount'), {})
        receipt_item = next((i for i in metadata_items if i.get('Name') == 'MpesaReceiptNumber'), {})
        phone_item = next((i for i in metadata_items if i.get('Name') == 'PhoneNumber'), {})

        amount = amount_item.get('Value')
        receipt = receipt_item.get('Value')
        phone = str(phone_item.get('Value'))

        # Validate required fields
        if not all([amount, receipt, phone]):
            return Response({'error': 'Missing required fields'}, status=400)

        # Prevent double-saving M-Pesa receipts
        if Contribution.objects.filter(reference=receipt, method='MPESA').exists():
            return Response({'message': 'Transaction already processed'}, status=200)

        # Get user by phone - return 404 if not found
        try:
            user = get_user_by_phone(phone)
        except Exception:
            return Response({'error': 'User not found'}, status=404)

        if not user:
            return Response({'error': 'User not found'}, status=404)

        try:
            chama = get_chama_for_user(user)
        except Exception:
            return Response({'error': 'Chama not found for user'}, status=404)

        if not chama:
            return Response({'error': 'Chama not found for user'}, status=404)

        # Use atomic transaction to ensure data consistency
        with transaction.atomic():
            try:
                # Find the user's membership
                member = Membership.objects.get(user=user, chama=chama)
            except Membership.DoesNotExist:
                return Response({'error': 'User is not a member of any chama'}, status=404)

            # Create a simple schedule for this contribution
            schedule = ContributionSchedule.objects.create(
                chama=chama,
                due_date=timezone.now().date(),
                expected_amount=amount
            )

            contribution = Contribution.objects.create(
                member=member,
                chama=chama,
                schedule=schedule,
                amount=amount,
                method='MPESA',
                reference=receipt,
                status='SUCCESS'
            )

            chama.balance += contribution.amount
            chama.save()

            ActivityLog.objects.create(
                user=user,
                chama=chama,
                action='CONTRIBUTION',
                details=f"M-Pesa contribution of KES {float(amount):.2f}"
            )

        return Response({'message': 'OK'}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


class ContributionScheduleViewSet(viewsets.ModelViewSet):
    """
    Nested routes under /chamas/<chama_id>/schedules/
    - SAFE methods allowed for ACTIVE members
    - POST/PUT/PATCH/DELETE allowed only for ACTIVE admins
    """
    serializer_class = ContributionScheduleSerializer
    permission_classes = [permissions.IsAuthenticated, IsChamaAdminOrReadOnly]
    lookup_field = 'id'

    def _get_chama(self):
        # explicit get_object_or_404 ensures a 404 when the chama is missing
        chama_id = self.kwargs.get('chama_id')
        return get_object_or_404(Chama, id=chama_id)

    def get_queryset(self):
        chama = self._get_chama()
        return ContributionSchedule.objects.filter(chama=chama).order_by('-due_date')

    def perform_create(self, serializer):
        chama = self._get_chama()
        # serializer's chama is read-only; set it server-side
        serializer.save(chama=chama)

    def perform_update(self, serializer):
        # Ensure chama is not changed
        chama = self._get_chama()
        serializer.save(chama=chama)

    def destroy(self, request, *args, **kwargs):
        # Default destroy is fine; get_queryset limits to the chama
        return super().destroy(request, *args, **kwargs)
