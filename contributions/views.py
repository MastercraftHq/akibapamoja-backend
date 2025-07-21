from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action, api_view, permission_classes
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
    ContributionStatusUpdateSerializer
)
from .permissions import IsChamaMember


class ContributionViewSet(viewsets.ModelViewSet):
    serializer_class = ContributionSerializer
    permission_classes = [permissions.IsAuthenticated, IsChamaMember]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return ContributionCreateSerializer
        elif self.action in ['partial_update', 'update_status']:
            return ContributionStatusUpdateSerializer
        return ContributionSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        chama_id = self.request.query_params.get('chama')
        if chama_id:
            context['chama'] = get_object_or_404(Chama, id=chama_id)
        return context

    def get_queryset(self):
        chama_id = self.request.query_params.get('chama')

        if chama_id:
            chama = get_object_or_404(Chama, id=chama_id)

            if self.request.user.is_staff:
                return Contribution.objects.filter(
                    chama=chama
                ).select_related('member__user', 'schedule')

            return Contribution.objects.filter(
                chama=chama,
                member__user=self.request.user
            ).select_related('schedule')

        # Fallback: return all if no chama provided (e.g., detail view)
        if self.request.user.is_staff:
            return Contribution.objects.all().select_related('member__user', 'schedule')

        return Contribution.objects.filter(
            member__user=self.request.user
        ).select_related('schedule')

    def perform_create(self, serializer):
        chama = self.get_serializer_context().get('chama')
        if not chama:
            raise PermissionDenied("Chama not found.")

        contribution = serializer.save(status='APPROVED')

        # Update chama balance
        chama.balance += contribution.amount
        chama.save()

        # Log activity
        ActivityLog.objects.create(
            user=self.request.user,
            chama=chama,
            action='CONTRIBUTION',
            details=f"Contribution of KES {contribution.amount:.2f} via {contribution.method}"
        )

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        PATCH /api/contributions/<id>/update-status/
        Only staff/admins can update status of a contribution.
        """
        contribution = self.get_object()
        user = request.user

        if not user.is_staff:
            raise PermissionDenied("Only admins can update contribution status.")

        if not user.chama_memberships.filter(chama=contribution.chama, is_admin=True).exists():
            raise PermissionDenied("You don't manage this Chama.")

        serializer = self.get_serializer(contribution, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def mpesa_callback(request):
    """
    Handle M-Pesa STK push callback.
    Expects receipt, amount, and phone from Safaricom.
    """
    try:
        data = request.data
        callback = data.get('Body', {}).get('stkCallback', {})
        metadata_items = callback.get('CallbackMetadata', {}).get('Item', [])

        amount_item = next((i for i in metadata_items if i.get('Name') == 'Amount'), {})
        receipt_item = next((i for i in metadata_items if i.get('Name') == 'MpesaReceiptNumber'), {})
        phone_item = next((i for i in metadata_items if i.get('Name') == 'PhoneNumber'), {})

        amount = amount_item.get('Value')
        receipt = receipt_item.get('Value')
        phone = str(phone_item.get('Value'))

        if not all([amount, receipt, phone]):
            return Response({'error': 'Missing required fields'}, status=400)

        if Contribution.objects.filter(reference=receipt, method='MPESA').exists():
            return Response({'message': 'Transaction already processed'}, status=200)

        user = get_user_by_phone(phone)  # Not yet implemented
        if not user:
            return Response({'error': 'User not found'}, status=404)

        chama = get_chama_for_user(user)  # Not yet implemented
        if not chama:
            return Response({'error': 'Chama not found for user'}, status=404)

        with transaction.atomic():
            member = Membership.objects.get(user=user, chama=chama)

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
                status='APPROVED'
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
