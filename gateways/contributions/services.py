from .models import Contribution
from groups.models import Group, Membership
from .exceptions import ContributionError
from .enums import PaymentMethod

class ContributionService:
    def get_group(self, slug):
        try:
            return Group.objects.get(slug=slug)
        except Group.DoesNotExist:
            raise ContributionError("Group with provided slug does not exist.")

    def validate_member(self, group, member_id):
        if not group.memberships.filter(user_id=member_id).exists():
            raise ContributionError("User is not a member of this group.")

    def validate_payment_method(self, method):
        if method not in PaymentMethod.values():
            raise ContributionError(f"Invalid payment method. Allowed: {', '.join(PaymentMethod.values())}")

    def create_contribution(self, group_slug, member_id, amount, payment_method, mpesa_transaction_id=None):
        group = self.get_group(group_slug)
        self.validate_member(group, member_id)
        self.validate_payment_method(payment_method)

        return Contribution.objects.create(
            group=group,
            member_id=member_id,
            amount=amount,
            payment_method=payment_method,
            mpesa_transaction_id=mpesa_transaction_id,
            status="recorded"
        )
