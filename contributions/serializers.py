from rest_framework import serializers
from chama.models import Membership, Chama
from contributions.models import Contribution, ContributionSchedule


class ContributionScheduleSerializer(serializers.ModelSerializer):
    chama_name = serializers.CharField(source='chama.name', read_only=True)

    class Meta:
        model = ContributionSchedule
        fields = [
            'id',
            'chama',
            'chama_name',
            'due_date',
            'expected_amount',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'chama_name']


class ContributionSerializer(serializers.ModelSerializer):
    member_username   = serializers.CharField(source='member.user.username', read_only=True)
    schedule_due_date = serializers.DateField(source='schedule.due_date',    read_only=True)
    chama_name        = serializers.CharField(source='schedule.chama.name',  read_only=True)

    class Meta:
        model = Contribution
        fields = [
            'id',
            'schedule',
            'schedule_due_date',
            'chama_name',
            'member',
            'member_username',
            'amount',
            'method',
            'status',
            'reference',
            'transaction_date',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'member_username', 'schedule_due_date', 'chama_name'
        ]

    def validate(self, attrs):
        status    = attrs.get('status') or self.instance.status
        reference = attrs.get('reference') or self.instance.reference

        if status == Contribution.Status.APPROVED and not reference:
            raise serializers.ValidationError("Approved contributions require a reference.")
        return attrs


class ContributionCreateSerializer(serializers.ModelSerializer):
    method = serializers.ChoiceField(choices=Contribution.PaymentMethod.choices, default=Contribution.PaymentMethod.CASH)

    class Meta:
        model = Contribution
        fields = [
            'schedule',
            'amount',
            'method',
        ]

    def validate(self, attrs):
        method = attrs.get('method') or Contribution.PaymentMethod.CASH
        if method == Contribution.PaymentMethod.MPESA:
            raise serializers.ValidationError({
                'method': 'Use M-Pesa callback for MPESA transactions.'
            })
        return attrs


class ContributionStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contribution
        fields = ['status']

    def validate_status(self, value):
        if self.instance.status != Contribution.Status.PENDING:
            raise serializers.ValidationError("Only pending contributions can be updated.")
        return value
