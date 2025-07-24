from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

from .models import Contribution, ActivityLog, ContributionSchedule
from chama.models import Chama, Membership
from .serializers import (
    ContributionSerializer,
    ContributionCreateSerializer,
    ContributionStatusUpdateSerializer
)
from .permissions import IsChamaMember, IsChamaAdmin

User = get_user_model()


# Utility functions
def get_user_by_phone(phone):
    try:
        return User.objects.get(phone_number=phone)
    except User.DoesNotExist:
        return None

def get_chama_for_user(user):
    membership = Membership.objects.filter(user=user).first()
    return membership.chama if membership else None

from chama.models import Chama, Membership

def get_chama_by_id_for_user(user, chama_id):
    """
    Returns a Chama instance if the user is a member of the given chama_id.
    Otherwise, returns None.
    """
    try:
        chama = Chama.objects.get(id=chama_id)
        if Membership.objects.filter(user=user, chama=chama).exists():
            return chama
    except Chama.DoesNotExist:
        return None
    return None



class ContributionViewSet(viewsets.ModelViewSet):
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
            contributions = Contribution.objects.filter(chama=chama)

            if self.request.user.is_staff:
                return contributions.select_related('member__user', 'schedule')
            return contributions.filter(member__user=self.request.user).select_related('schedule')

        if self.request.user.is_staff:
            return Contribution.objects.all().select_related('member__user', 'schedule')
        return Contribution.objects.filter(member__user=self.request.user).select_related('schedule')

    def perform_create(self, serializer):
        chama = self.get_serializer_context().get('chama')
        if not chama:
            raise PermissionDenied("Chama not found.")

        method = serializer.validated_data.get('method', 'CASH')
        
        # Auto-approve MPESA payments
        status = 'APPROVED' if method == 'MPESA' else 'PENDING'
        
        contribution = serializer.save(
            chama=chama,
            method=method,
            status=status
        )

        ActivityLog.objects.create(
            user=self.request.user,
            chama=chama,
            action='CONTRIBUTION',
            details=f"Contribution of KES {contribution.amount:.2f} via {method} ({status})"
        )

    def update_status(self, request, pk=None):
        """
        PATCH /api/contributions/<id>/update-status/
        Only chama admins can update a contribution's status.
        """
        contribution = self.get_object()

        serializer = self.get_serializer(contribution, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_contribution = serializer.save()

        # If the status changed from non-approved to approved
        if updated_contribution.status == 'APPROVED' and contribution.status != 'APPROVED':
            contribution.chama.balance += contribution.amount
            contribution.chama.save()

            ActivityLog.objects.create(
                user=request.user,
                chama=contribution.chama,
                action='CONTRIBUTION',
                details=f"Manual contribution of KES {contribution.amount:.2f} approved by admin"
            )

        return Response(serializer.data, status=status.HTTP_200_OK)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_callback(request):
    """
    Handle incoming payment confirmation from M-Pesa.
    This endpoint automatically records approved contributions with MPESA method.

    Expected payload:
    {
        "phone_number": "2547XXXXXX",  # Format: 2547...
        "amount": 1000,               # Positive number
        "reference": "MPESA12345",   # Unique transaction ID
        "chama_id": "abc-123",       # UUID of the chama
        "timestamp": "20230724...",   # Optional: Payment timestamp
        "first_name": "John",        # Optional: Payer details
        "last_name": "Doe"
    }
    """
    try:
        data = request.data
        
        # Validate required fields
        required_fields = ['phone_number', 'amount', 'reference', 'chama_id']
        if not all(field in data for field in required_fields):
            return Response(
                {"detail": "Missing required fields. Need: phone_number, amount, reference, chama_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse and validate data
        phone = data['phone_number']
        try:
            amount = float(data['amount'])
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid amount. Must be a positive number"},
                status=status.HTTP_400_BAD_REQUEST
            )

        reference = data['reference']
        chama_id = data['chama_id']

        # Get user and validate chama membership
        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found for the provided phone number"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            chama = Chama.objects.get(id=chama_id)
            if not Membership.objects.filter(user=user, chama=chama).exists():
                return Response(
                    {"detail": "User is not a member of this chama"},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Chama.DoesNotExist:
            return Response(
                {"detail": "Chama not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Process payment in atomic transaction
        with transaction.atomic():
            # Check for duplicate transaction (reference must be unique for MPESA)
            if Contribution.objects.filter(reference=reference, method='MPESA').exists():
                return Response(
                    {
                        "detail": "Payment already processed",
                        "reference": reference,
                        "status": "DUPLICATE"
                    },
                    status=status.HTTP_409_CONFLICT
                )

            # Get the membership record
            membership = Membership.objects.get(user=user, chama=chama)

            # Create the contribution record
            contribution = Contribution.objects.create(
                chama=chama,
                member=membership,
                amount=amount,
                method='MPESA',  # Automatically set for M-Pesa payments
                status='APPROVED',  # Auto-approved
                reference=reference,
                transaction_date=data.get('timestamp') or timezone.now()
            )

            # Update chama balance
            chama.balance += amount
            chama.save()

            # Create activity log
            ActivityLog.objects.create(
                user=user,
                chama=chama,
                action='CONTRIBUTION',
                details=(
                    f"M-Pesa contribution of KES {amount:.2f} from "
                    f"{user.get_full_name() or phone} (Ref: {reference})"
                )
            )

            # Prepare response data
            response_data = {
                "status": "success",
                "contribution_id": str(contribution.id),
                "chama_id": str(chama.id),
                "member_id": str(user.id),
                "amount": amount,
                "reference": reference,
                "new_balance": chama.balance,
                "timestamp": contribution.transaction_date.isoformat()
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        # Log the unexpected error for debugging
        logger.error(f"Error processing M-Pesa callback: {str(e)}", exc_info=True)
        return Response(
            {"detail": "An error occurred while processing your payment", "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )