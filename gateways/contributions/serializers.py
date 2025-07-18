from rest_framework import serializers
from .models import Contribution

class CreateContributionSerializer(serializers.Serializer):
    groupId = serializers.SlugField()
    memberId = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    paymentMethod = serializers.CharField()
    mpesaTransactionId = serializers.CharField(required=False, allow_blank=True)

class ContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contribution
        fields = [
            'id', 'group', 'member', 'amount', 'payment_method',
            'mpesa_transaction_id', 'date', 'status'
        ]
