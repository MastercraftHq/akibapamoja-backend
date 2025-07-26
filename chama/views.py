from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404


from .enums import (
    MembershipRole,
    MembershipStatus,
)
from .models import Chama, Membership
from .serializers import ChamaSerializer, MembershipSerializer,JoinChamaSerializer
from .permissions import IsChamaAdmin, IsChamaMember

User = get_user_model()

class ChamaViewSet(viewsets.ModelViewSet):
    queryset = Chama.objects.all()
    serializer_class = ChamaSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """
        When a Chama is created, automatically assign the
        requesting user as an ADMIN member of that Chama.
        """

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
        """
        GET /chamas/{pk}/members/
        Any member can list all other members.
        """

        members = Membership.objects.filter(chama_id=pk)
        serializer = MembershipSerializer(members, many=True)
        return Response(serializer.data)
    
class ListMembersView(generics.ListAPIView):
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, IsChamaMember]

    def get_queryset(self):
        chama = get_object_or_404(Chama, id=self.kwargs['groupId'])
        return Membership.objects.filter(chama=chama)

class JoinChamaView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = JoinChamaSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        chama = serializer.validated_data['join_code']  
        membership = Membership.objects.create(
            user=request.user,
            chama=chama,
            role=Membership.Role.MEMBER,
            status=Membership.Status.PENDING
        )
        
        return Response({
            "message": "Join request submitted successfully. Awaiting admin approval.",
            "membership": MembershipSerializer(membership).data
        }, status=status.HTTP_201_CREATED)