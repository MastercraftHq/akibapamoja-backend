from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema

from .enums import (
    MembershipRole,
    MembershipStatus,
    ContributionFrequency,
    ContributionStatus
)
from .models import Chama, Membership, ContributionSchedule
from .serializers import ChamaSerializer, MembershipSerializer, ContributionScheduleSerializer
from .permissions import IsChamaAdmin, IsChamaMember

User = get_user_model()

class ChamaViewSet(viewsets.ModelViewSet):
    queryset = Chama.objects.all()
    serializer_class = ChamaSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        chama = serializer.save()
        Membership.objects.create(
            user=self.request.user,
            chama=chama,
            role=MembershipRole.ADMIN.value,
            status=MembershipStatus.ACTIVE.value
        )

    @swagger_auto_schema(
        operation_description="Add a new member to the Chama",
        request_body=MembershipSerializer,
        responses={201: MembershipSerializer()}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsChamaAdmin])
    def add_member(self, request, pk=None):
        chama = self.get_object()
        serializer = MembershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(chama=chama)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @swagger_auto_schema(
        operation_description="List all members of the Chama",
        responses={200: MembershipSerializer(many=True)}
    )
    @action(detail=True, methods=['get'], permission_classes=[IsChamaMember])
    def members(self, request, pk=None):
        members = Membership.objects.filter(chama_id=pk)
        serializer = MembershipSerializer(members, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        operation_description="Add a contribution schedule",
        request_body=ContributionScheduleSerializer,
        responses={201: ContributionScheduleSerializer()}
    )
    @action(detail=True, methods=['post'], permission_classes=[IsChamaAdmin])
    def add_schedule(self, request, pk=None):
        chama = self.get_object()
        serializer = ContributionScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(chama=chama)
        return Response(serializer.data, status=status.HTTP_201_CREATED)