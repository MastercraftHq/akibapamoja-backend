# validators.py
from django.core.exceptions import ValidationError
from .enums import ContributionFrequency

def validate_future_date(value):
    """Validate that date is in the future"""
    if value < __import__('django').utils.timezone.now().date():
        raise ValidationError('Date cannot be in the past')

def validate_contribution_day(value, frequency):
    """Validate due_day based on frequency (accepts uppercase enum.value strings)."""
    if not isinstance(value, int):
        raise ValidationError('Due day must be an integer')

    # Normalize to lowercase so "WEEKLY", "weekly", or ContributionFrequency.WEEKLY.value all work
    freq = frequency.lower()

    if freq == ContributionFrequency.WEEKLY.value.lower():
        if not 1 <= value <= 7:
            raise ValidationError('For weekly frequency, day must be between 1-7')

    elif freq == ContributionFrequency.MONTHLY.value.lower():
        if not 1 <= value <= 31:
            raise ValidationError('For monthly frequency, day must be between 1-31')

    elif freq == ContributionFrequency.QUARTERLY.value.lower():
        # quarterly treated like monthly
        if not 1 <= value <= 31:
            raise ValidationError('For quarterly frequency, day must be between 1-31')

    elif freq == ContributionFrequency.DAILY.value.lower():
        # daily could be any day-of-month or day-of-week; adjust as needed.
        # Here we'll allow 1-31
        if not 1 <= value <= 31:
            raise ValidationError('For daily frequency, day must be between 1-31')

    else:
        raise ValidationError('Invalid frequency specified')
