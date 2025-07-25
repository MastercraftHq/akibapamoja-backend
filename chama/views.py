from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model

from .models import Chama, Membership
from .serializers import ChamaSerializer, MembershipSerializer
from .permissions import IsChamaAdmin, IsChamaMember

User = get_user_model()


class ChamaCreateView(generics.CreateAPIView):
    serializer_class = ChamaSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        chama = serializer.save()
        Membership.objects.create(
            user=self.request.user,
            chama=chama,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE
        )


class ChamaDetailView(generics.RetrieveAPIView):
    serializer_class = ChamaSerializer
    queryset = Chama.objects.all()
    permission_classes = [IsAuthenticated]


class AddMemberView(generics.CreateAPIView):
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, IsChamaAdmin]

    def create(self, request, *args, **kwargs):
        chama = get_object_or_404(Chama, id=kwargs['groupId'])

        email = request.data.get('email')
        role = request.data.get('role', Membership.Role.MEMBER)
        user = get_object_or_404(User, email=email)

        membership, created = Membership.objects.get_or_create(
            user=user,
            chama=chama,
            defaults={"role": role, "status": Membership.Status.INVITED}
        )
        serializer = MembershipSerializer(membership)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ListMembersView(generics.ListAPIView):
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, IsChamaMember]

    def get_queryset(self):
        chama = get_object_or_404(Chama, id=self.kwargs['groupId'])
        return Membership.objects.filter(chama=chama).order_by('id')
