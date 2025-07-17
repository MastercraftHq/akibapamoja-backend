import uuid

from .models import Membership, Group
from .exceptions import GroupNotFoundError

def generate_invite_code():
    return str(uuid.uuid4())

def get_group_or_404(slug):
    try:
        return Group.objects.get(slug=slug)
    except Group.DoesNotExist:
        raise GroupNotFoundError()

def is_member(user, group):
    return Membership.objects.filter(user=user, group=group).exists()

def is_admin(user, group):
    return Membership.objects.filter(user=user, group=group, role='admin').exists()

def get_display_name(user):
    return user.get_full_name() or user.username or user.email
