from rest_framework import serializers
from .models import Contribution

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
        
        def create(self, validated_data):
            validated_data["user"] = self.context["request"].user
            return super().create(validated_data)