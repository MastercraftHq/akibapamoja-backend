from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from .models import Contribution, ActivityLog, ContributionSchedule
from chama.models import Chama, Membership
from .serializers import ContributionSerializer, ContributionCreateSerializer
from .permissions import IsChamaMember
from .utils import get_user_by_phone, get_chama_for_user

class ContributionViewSet(viewsets.ModelViewSet):
    serializer_class = ContributionSerializer
    permission_classes = [permissions.IsAuthenticated, IsChamaMember]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['member']
    ordering = ['-created_at']

    def get_queryset(self):
        chama_id = self.kwargs.get('chama_id')
        if not chama_id:
            raise PermissionDenied("Chama ID is required")
        chama = get_object_or_404(Chama, id=chama_id)
        
        if not Membership.objects.filter(user=self.request.user, chama=chama, status=Membership.Status.ACTIVE).exists():
            raise PermissionDenied("You are not a member of this Chama")
        
        if Membership.objects.filter(
            user=self.request.user,
            chama=chama,
            role__in=[Membership.Role.ADMIN, Membership.Role.TREASURER],
            status=Membership.Status.ACTIVE
        ).exists():
            return Contribution.objects.filter(chama=chama).select_related('member__user', 'schedule')
        return Contribution.objects.filter(
            chama=chama,
            member__user=self.request.user
        ).select_related('member__user', 'schedule')

    def get_serializer_class(self):
        if self.action == 'create':
            return ContributionCreateSerializer
        return ContributionSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        chama_id = self.kwargs.get('chama_id')
        context['chama'] = get_object_or_404(Chama, id=chama_id) if chama_id else None
        return context
    
    def perform_create(self, serializer):
        chama = self.get_serializer_context().get('chama')
        if not chama:
            raise PermissionDenied("Chama not found")
        
        contribution = serializer.save()
        chama.balance += contribution.amount
        chama.save()
        
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
    data = request.data
    try:
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

        with transaction.atomic():
            try:
                member = Membership.objects.get(user=user, chama=chama, status=Membership.Status.ACTIVE)
            except Membership.DoesNotExist:
                return Response({'error': 'User is not a member of any chama'}, status=404)
            
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