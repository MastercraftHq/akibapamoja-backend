from django.db import transaction
from django.db.models import F
import uuid
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from rest_framework.response import Response
from contributions.services.mpesa import MpesaDarajaClient
from django.urls import reverse
from django.utils import timezone
import requests
from rest_framework.decorators import authentication_classes

from chama.models import Membership
from .models import Contribution, ContributionSchedule
from .serializers import (
    ContributionSerializer,
    ContributionCreateSerializer,
    ContributionStatusUpdateSerializer
)


class ContributionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return ContributionCreateSerializer
        if self.action == 'update_status':
            return ContributionStatusUpdateSerializer
        return ContributionSerializer

    def get_queryset(self):
        """
        List/filter by chama via schedule or allow staff to see all.
        """
        qs = Contribution.objects.select_related('schedule__chama', 'member__user')

        #+for update_status we want to fetch any contribution
        if self.action == 'update_status':
            return qs

        # allow filtering by chama for non-staff
        chama_id = self.request.query_params.get('chama')
        if chama_id:
            qs = qs.filter(schedule__chama_id=chama_id)

        if self.request.user.is_staff:
            return qs

        # non-staff users must belong to the chama
        if not chama_id:
            return Contribution.objects.none()

        try:
            membership = Membership.objects.get(
                user=self.request.user,
                chama_id=chama_id
            )
        except Membership.DoesNotExist:
            return Contribution.objects.none()

        # ADMIN/TREASURER sees all; MEMBER sees only their own
        if membership.role in (
            Membership.Role.ADMIN,
            Membership.Role.TREASURER
        ):
            return qs
        return qs.filter(member=membership)

    def create(self, request, *args, **kwargs):
        """
        - Manual contributions: method=CASH, status=PENDING  
        - M-Pesa in callback only; clients cannot create MPESA here  
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        schedule = serializer.validated_data['schedule']
        amount   = serializer.validated_data['amount']
        method   = serializer.validated_data.get('method') or Contribution.PaymentMethod.CASH

        # verify membership
        try:
            membership = Membership.objects.get(
                user=request.user,
                chama=schedule.chama
            )
        except Membership.DoesNotExist:
            raise PermissionDenied("You are not a member of this Chama.")

        # enforce manual-payment rules
        if method == Contribution.PaymentMethod.MPESA:
            raise ValidationError({'method': 'Use M-Pesa callback for MPESA transactions.'})

        status_val = Contribution.Status.PENDING

        with transaction.atomic():
            contrib = Contribution.objects.create(
                schedule=schedule,
                member=membership,
                amount=amount,
                method=Contribution.PaymentMethod.CASH,
                status=status_val
            )

        output = ContributionSerializer(contrib, context={'request': request}).data
        return Response(output, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        Only chama ADMIN/TREASURER may change status of PENDING contributions.
        """
        contrib = self.get_object()
        user    = request.user

        # verify admin/treasurer role
        if not Membership.objects.filter(
            user=user,
            chama=contrib.schedule.chama,
            role__in=[Membership.Role.ADMIN, Membership.Role.TREASURER]
        ).exists():
            raise PermissionDenied("Only chama admins or treasurers can update status.")

        # only pending may change
        if contrib.status != Contribution.Status.PENDING:
            raise ValidationError({'status': 'Only pending contributions can be updated.'})

        serializer = self.get_serializer(contrib, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']

        with transaction.atomic():
            serializer.save()
            # bump balance on approval
            if new_status == Contribution.Status.APPROVED:
                chama = contrib.schedule.chama
                chama.balance = F('balance') + contrib.amount
                chama.save(update_fields=['balance'])

        return Response({'detail': 'Status updated successfully.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='initiate-mpesa')
    def initiate_mpesa(self, request):
        """
        Kick off an STK Push for a member’s scheduled contribution.
        """
        user = request.user
        schedule_id = request.data.get('schedule')
        amount      = request.data.get('amount')

        # Validate schedule & membership
        try:
            schedule_uuid = uuid.UUID(schedule_id)
            schedule = ContributionSchedule.objects.get(id=schedule_uuid)
        except (ValueError, DjangoValidationError, ContributionSchedule.DoesNotExist):
            raise ValidationError({'schedule': 'Invalid schedule ID.'})
        except Membership.DoesNotExist:
            raise PermissionDenied('Not a member of this Chama.')
        

        # verify membership
        try:
            Membership.objects.get(user=user, chama=schedule.chama)
        except Membership.DoesNotExist:
            raise PermissionDenied('Not a member of this Chama.')

        # Build callback URL for Daraja to hit
        callback_url = request.build_absolute_uri(reverse('mpesa-callback'))

        # Use schedule ID + timestamp as reference
        reference = f"{schedule_id}-{int(timezone.now().timestamp())}"

        # STK Push
        try:
            resp = MpesaDarajaClient.initiate_stk_push(
                phone_number=user.phone,
                amount=amount,
                reference=reference,
                callback_url=callback_url
            )
        except requests.HTTPError as e:
            raise ValidationError({'mpesa': 'Failed to initiate STK Push.'})

        return Response({
            'CheckoutRequestID': resp.get('CheckoutRequestID'),
            'ResponseCode':      resp.get('ResponseCode'),
            'ResponseDescription': resp.get('ResponseDescription'),
            'MerchantRequestID': resp.get('MerchantRequestID'),
            'reference':         reference
        }, status=200)

@api_view(['POST'])  # must be outermost
@authentication_classes([])  # disables auth
@permission_classes([])  # disables permission checks
@csrf_exempt  # optional, but helpful for external services
def mpesa_callback(request):
    """
    Endpoint for M-Pesa payment confirmations.
    """
    print(">>> mpesa_callback view HIT")
    required = ['phone', 'amount', 'reference', 'chama_id', 'schedule_id']
    missing  = [f for f in required if not request.data.get(f)]
    if missing:
        return Response(
            {'error': f"Missing required fields: {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    phone     = request.data['phone']
    reference = request.data['reference'].strip()
    amount    = request.data['amount']
    schedule_id = request.data['schedule_id']
    chama_id  = request.data['chama_id']

    # lookup user & membership
    from users.models import User
    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        raise NotFound("User not found.")

    try:
        schedule = ContributionSchedule.objects.get(id=schedule_id, chama_id=chama_id)
    except (ContributionSchedule.DoesNotExist, ValueError, DjangoValidationError):
        raise ValidationError({'schedule_id': 'Invalid schedule or Chama ID.'})

    # 3) ensure the user actually belongs to that Chama
    try:
        membership = Membership.objects.get(user=user, chama_id=chama_id)
    except Membership.DoesNotExist:
        raise PermissionDenied("User is not a member of this Chama.")


    # enforce idempotency
    if Contribution.objects.filter(
        schedule=schedule,
        reference=reference
    ).exists():
        return Response(
            {'status': 'DUPLICATE', 'message': 'Contribution already recorded.'},
            status=status.HTTP_409_CONFLICT
        )

    # record contribution & bump balance
    with transaction.atomic():
        contrib = Contribution.objects.create(
            schedule=schedule,
            member=membership,
            amount=amount,
            method=Contribution.PaymentMethod.MPESA,
            status=Contribution.Status.APPROVED,
            reference=reference
        )
        chama = schedule.chama
        chama.balance = F('balance') + contrib.amount
        chama.save(update_fields=['balance'])

    return Response(
        {'status': 'success', 'message': 'M-Pesa contribution recorded.'},
        status=status.HTTP_201_CREATED
    )