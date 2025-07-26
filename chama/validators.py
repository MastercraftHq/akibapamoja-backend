# validators.py
from django.core.exceptions import ValidationError

def validate_future_date(value):
    """Validate that date is in the future"""
    if value < __import__('django').utils.timezone.now().date():
        raise ValidationError('Date cannot be in the past')