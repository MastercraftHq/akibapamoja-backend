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
from .serializers import ContributionSerializer, ContributionCreateSerializer
from .permissions import IsChamaMember
from .utils import get_user_by_phone, get_chama_for_user

class ContributionViewSet(viewsets.ModelViewSet):
    serializer_class   = ContributionSerializer
    permission_classes = [permissions.IsAuthenticated, IsChamaMember]
    filter_backends    = [filters.OrderingFilter]
    ordering           = ['-created_at']

    def get_queryset(self):
        # Get chama_id from query params
        chama_id = self.request.query_params.get('chama')
        chama = get_object_or_404(Chama, id=chama_id) if chama_id else None
        
        # Ensure user is a member of the chama
        if chama and not Membership.objects.filter(user=self.request.user, chama=chama).exists():
            raise PermissionDenied("You are not a member of this Chama.")
        
        # Regular memebers can only see their contributions
        # Admins and treasurers can see all contributions in the chama
        if chama and self.request.user.is_staff:
            return Contribution.objects.filter(chama=chama).select_related('member__user', 'schedule').order_by('-transaction_date')
        else:
            return Contribution.objects.filter(
                chama=chama,
                member__user=self.request.user
            ).select_related('schedule').order_by('-transaction_date') if chama else Contribution.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ContributionCreateSerializer
        return ContributionSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Get chama_id from query params
        chama_id = self.request.query_params.get('chama')
        context['chama'] = get_object_or_404(Chama, id=chama_id) if chama_id else None
        return context
    
    # Create a manual contribution
    def perform_create(self, serializer):
        chama = self.get_serializer_context().get('chama')
        if not chama:
            raise PermissionDenied("Chama not found.")
        
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
            details=f"Manual contribution of KES {serializer.validated_data['amount']:.2f}"
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
        amount_item  = next((i for i in metadata_items if i.get('Name') == 'Amount'), {})
        receipt_item = next((i for i in metadata_items if i.get('Name') == 'MpesaReceiptNumber'), {})
        phone_item   = next((i for i in metadata_items if i.get('Name') == 'PhoneNumber'), {})

        amount  = amount_item.get('Value')
        receipt = receipt_item.get('Value')
        phone   = str(phone_item.get('Value'))

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
