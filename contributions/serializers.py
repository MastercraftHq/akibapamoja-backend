from rest_framework import serializers
from django.utils import timezone
from django.db import models
from .models import Contribution, ContributionCycle, ContributionSchedule
from chama.models import Membership
from django.contrib.auth import get_user_model

User = get_user_model()

class ContributionSerializer(serializers.ModelSerializer):
    
    user = serializers.ReadOnlyField(source="user.id")
    status = serializers.ReadOnlyField()

    class Meta:
        model = Contribution
        fields = [
            "id", "user", "chama", "amount", "method",
            "reference", "status", "notes", "created_at"
        ]
        read_only_fields = ["id", "user", "status", "created_at"]

        def validate_amount(self, value):
            if value <= 0:
                raise serializers.ValidationError("Amount must be grater than 0")
            raise value
        
        def validate_member_id(self, value):
            chama = self.context.get('chama')
            if not Membership.objects.filter(
                chama=chama, id=value
            ).exists():
                raise serializers.ValidationError("Member does not belong to this chama.")
        
        def create(self, validated_data):
            validated_data["chama"] = self.context["chama"] 
            validated_data["user"] = self.context["request"].user
            return super().create(validated_data)
        
class ContributionScheduleSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.id")
    is_overdue = serializers.SerializerMethodField()
    amount_paid = serializers.SerializerMethodField()
    amount_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = ContributionSchedule
        fields = [
            'id', 'user', 'due_date', 'expected_amount',
            'status', 'chama', 'is_overdue', 'amount_paid',
            'amount_remaining', 'created_at'
        ]
        
    def get_is_overdue(self, obj):
        return obj.due_date < timezone.now().date() and obj.status in ['PENDING', 'PARTIAL']
    
    def get_amount_paid(self, obj):
        contributions = Contribution.objects.filter(
            schedule=obj,
            is_confirmed=True
        ).aggregate(total=models.Sum('amount'))
        return contributions['total'] or 0.00
    
    def get_amount_remaining(self, obj):
        amount_paid = self.get_amount_paid(obj)
        return obj.expected_amount - amount_paid if obj.expected_amount else 0.00
    
class ContributionCreateSerializer(serializers.ModelSerializer):
    member_id = serializers.UUIDField()
    
    class Meta:
        model = Contribution
        fields = [
            'member_id', 'amount', 'method', 'transaction_date',
            'notes', 'reference'
        ]
        
    def validate_member_id(self, value):
        chama = self.context.get('chama')
        try:
            member = chama.members.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Member does not belong to this chama.")
        return member.id
    def create(self, validated_data):
        member_id = validated_data.pop('member_id')
        chama = self.context.get('chama')
        member = chama.members.get(id=member_id)
        validated_data['user'] = member.user
        validated_data['chama'] = chama
        return super().create(validated_data)