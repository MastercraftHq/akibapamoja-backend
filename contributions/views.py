from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt

from .models import Contribution, ActivityLog
from .serializers import ContributionSerializer
from .permissions import IsChamaMember
from .utils import get_user_by_phone, get_chama_for_user

class ContributionViewSet(viewsets.ModelViewSet):
    serializer_class   = ContributionSerializer
    permission_classes = [permissions.IsAuthenticated, IsChamaMember]
    filter_backends    = [filters.OrderingFilter]
    ordering           = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs = Contribution.objects.filter(chama__membership__user=user)
        chama_id = self.request.query_params.get('chama')
        if chama_id:
            qs = qs.filter(chama_id=chama_id)
        return qs

    def perform_create(self, serializer):
        chama = serializer.validated_data['chama']
        user  = self.request.user
        if not chama.membership_set.filter(user=user).exists():
            raise PermissionDenied("You are not a member of this chama.")

        contribution = serializer.save(user=user)

        # Update chama balance
        chama.balance += contribution.amount
        chama.save()

        # Log the activity
        ActivityLog.objects.create(
            user=user,
            chama=chama,
            action='CONTRIBUTION',
            details=f"{user.username} contributed KES {contribution.amount}"
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

        user  = get_user_by_phone(phone)
        chama = get_chama_for_user(user)

        contribution = Contribution.objects.create(
            user=user,
            chama=chama,
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
            details=f"M-Pesa contribution of KES {amount}"
        )

        return Response({'message': 'OK'}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)