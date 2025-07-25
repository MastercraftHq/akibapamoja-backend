from django.db import transaction
from django.db.models import F
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound

from activity.models import ActivityLog
from chama.models import Chama, Membership
from users.models import User

from .models import Contribution
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
        # allow update_status to fetch *any* contribution
        if self.action == 'update_status':
            return Contribution.objects.all()

        chama_id = self.request.query_params.get('chama')
        if not chama_id:
            return Contribution.objects.none()

        qs = Contribution.objects.filter(chama_id=chama_id)

        # superusers & staff see everything for that chama
        if self.request.user.is_staff:
            return qs

        # find *your* membership in that chama
        try:
            membership = Membership.objects.get(
                user=self.request.user, chama_id=chama_id
            )
        except Membership.DoesNotExist:
            return Contribution.objects.none()

        # ADMIN/TREASURER sees all; plain member only their own
        if membership.role in (
            Membership.Role.ADMIN,
            Membership.Role.TREASURER
        ):
            return qs

        return qs.filter(member__user=self.request.user)

    def create(self, request, *args, **kwargs):
        user = request.user

        # 1. Resolve current chama & membership
        chama_id = request.query_params.get('chama')
        if not chama_id:
            raise ValidationError({'chama': 'This query parameter is required.'})
        try:
            chama = Chama.objects.get(id=chama_id)
        except Chama.DoesNotExist:
            raise ValidationError({'chama': 'Invalid chama ID.'})

        try:
            membership = Membership.objects.get(user=user, chama=chama)
        except Membership.DoesNotExist:
            raise PermissionDenied('You are not a member of this chama.')

        # 2. Validate input (includes schedule!)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        schedule  = data['schedule']
        amount    = data['amount']
        method    = data.get('method', Contribution.PaymentMethod.CASH)
        reference = data.get('reference', '').strip()

        # 3. MPESA rules
        if method == Contribution.PaymentMethod.MPESA:
            if not reference:
                raise ValidationError({'reference': 'M-Pesa reference is required.'})
            if Contribution.objects.filter(reference=reference).exists():
                raise ValidationError({'reference': 'Duplicate reference.'})
            status_val = Contribution.Status.APPROVED
        else:
            status_val = Contribution.Status.PENDING

        # 4. Create + balance bump + log
        with transaction.atomic():
            contribution = Contribution.objects.create(
                member=membership,
                chama=chama,
                schedule=schedule,
                amount=amount,
                method=method,
                reference=reference,
                status=status_val,
            )

            if status_val == Contribution.Status.APPROVED:
                chama.balance = F('balance') + amount
                chama.save(update_fields=['balance'])

            ActivityLog.objects.create(
                chama=chama,
                user=user,
                message=(
                    f'Contribution {contribution.id} of '
                    f'{amount} created with status={status_val}.'
                )
            )

        # 5. Return full representation
        out = ContributionSerializer(contribution, context={'request': request}).data
        return Response(out, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=['patch'],
        url_path='update-status',
        permission_classes=[permissions.IsAuthenticated]
    )
    def update_status(self, request, pk=None):
        contribution = self.get_object()
        user = request.user

        # only chama ADMIN/TREASURER may change status
        if not Membership.objects.filter(
            user=user,
            chama=contribution.chama,
            role__in=[Membership.Role.ADMIN, Membership.Role.TREASURER]
        ).exists():
            raise PermissionDenied(
                'Only chama admins or treasurers can update status.'
            )

        if contribution.status != Contribution.Status.PENDING:
            raise ValidationError(
                {'status': 'Only pending contributions can be updated.'}
            )

        serializer = self.get_serializer(
            contribution, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        old_status = contribution.status

        with transaction.atomic():
            serializer.save()
            if old_status != Contribution.Status.APPROVED \
               and new_status == Contribution.Status.APPROVED:
                chama = contribution.chama
                chama.balance = F('balance') + contribution.amount
                chama.save(update_fields=['balance'])

            ActivityLog.objects.create(
                chama=contribution.chama,
                user=user,
                message=(
                    f'Contribution {contribution.id} status '
                    f'changed from {old_status} to {new_status}.'
                )
            )

        return Response(
            {'detail': 'Contribution status updated successfully.'},
            status=status.HTTP_200_OK
        )


@api_view(['POST'])
@permission_classes([])   # open for M-Pesa callbacks
def mpesa_callback(request):
    required = ('phone', 'amount', 'reference', 'chama_id')
    missing = [f for f in required if not request.data.get(f)]
    if missing:
        return Response(
            {'error': f'Missing required fields: {", ".join(missing)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # lookup user + membership
    phone = request.data['phone']
    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        raise NotFound('User not found.')

    try:
        chama = Chama.objects.get(id=request.data['chama_id'])
        membership = Membership.objects.get(user=user, chama=chama)
    except Chama.DoesNotExist:
        raise ValidationError({'chama_id': 'Invalid chama ID.'})
    except Membership.DoesNotExist:
        raise PermissionDenied('User is not a member of this chama.')

    reference = request.data['reference']
    if Contribution.objects.filter(reference=reference).exists():
        return Response(
            {'status': 'DUPLICATE',
             'message': 'Contribution with this reference already exists'},
            status=status.HTTP_409_CONFLICT
        )

    # record + bump + log
    with transaction.atomic():
        contribution = Contribution.objects.create(
            member=membership,
            chama=chama,
            amount=request.data['amount'],
            method=Contribution.PaymentMethod.MPESA,
            reference=reference,
            status=Contribution.Status.APPROVED
        )
        chama.balance = F('balance') + contribution.amount
        chama.save(update_fields=['balance'])

        ActivityLog.objects.create(
            chama=chama,
            user=user,
            message=(
                f'M-Pesa contribution recorded (ref={reference}, '
                f'amount={contribution.amount}).'
            )
        )

    return Response(
        {'status': 'success', 'message': 'M-Pesa contribution recorded.'},
        status=status.HTTP_201_CREATED
    )