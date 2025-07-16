from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import get_object_or_404
from chama.models import Chama

User = get_user_model()

def _normalize_phone(phone: str) -> str:
    """Ensure phone is in 2547XXXXXXXX format (simplistic normalizer)."""
    phone = phone.strip()
    if phone.startswith('+'):
        phone = phone[1:]
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    return phone

def get_user_by_phone(phone: str):
    """Return the User whose `phone` field matches the provided number."""
    phone = _normalize_phone(phone)
    return get_object_or_404(User, phone=phone)

def get_chama_for_user(user):
    """Return the first chama the user belongs to, else raise 404."""
    chama = Chama.objects.filter(membership_set__user=user).first()
    if not chama:
        raise Http404("User is not a member of any chama.")
    return chama