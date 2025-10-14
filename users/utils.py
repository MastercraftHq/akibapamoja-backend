from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password, make_password
from django.conf import settings
from django.db import transaction
from users.models import OTP, SMSDevice, User
from .exceptions import OTPSendError
import secrets
import logging
from django.core.cache import cache

def generate_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "authToken": str(refresh.access_token),
        "refreshToken": str(refresh)
    }

def generate_otp_code(length=6):
    return f"{secrets.randbelow(10**length):0{length}d}"

def send_otp(phone, otp_code=None, purpose="login"):
    """Send an OTP code to the user's phone number"""
    logger = logging.getLogger(__name__)
    if not phone:
        raise ValueError("Phone number is required.")

    # Rate limiting
    count_key = f"otp:count:{phone}"
    cooldown_key = f"otp:cooldown:{phone}"
    max_sends = 5 
    window_seconds = 600  
    cooldown_seconds = 60  

    # Check cooldown
    if cache.get(cooldown_key):
        raise OTPSendError("Please wait before requesting another OTP.")

    # Check and increment send count
    current_count = cache.get(count_key)
    if current_count is None:
        cache.set(count_key, 0, timeout=window_seconds)
        current_count = 0

    if current_count >= max_sends:
        raise OTPSendError("OTP request limit exceeded. Try again later.")

    cache.incr(count_key)

    device, _ = SMSDevice.objects.get_or_create(
        phone_number=phone,
        defaults={'name': f"SMS Device for {phone}"}
    )

    try:
        user = User.objects.get(phone=phone)
        device.user = user
        device.save()
    except User.DoesNotExist:
        logger.error(f"User not found for phone {phone}")
        raise OTPSendError("User not found. Please try again.")

    # Generate and send hashed OTP via device
    if otp_code is None:
        otp_code = device.generate_challenge()
    else:
        hashed_code = make_password(otp_code)
        device.current_token = hashed_code
        device.token_timestamp = timezone.now()
        device.save()

    success = device.send_token(token=otp_code)
    if not success:
        cache.decr(count_key)
        logger.error(f"Failed to send OTP to {phone}")
        raise OTPSendError("Failed to send OTP. Please try again.")
    
    # Set cooldown after successful send
    cache.set(cooldown_key, True, timeout=cooldown_seconds)
    
    # Atomically mark previous active OTPs as used and create new one
    with transaction.atomic():
        OTP.objects.filter(
            phone=phone,
            purpose=purpose,
            is_used=False,
            expires_at__gt=timezone.now()
        ).update(is_used=True)
        
        OTP.objects.create(
            phone=phone,
            hashed_code=make_password(otp_code),
            purpose=purpose,
        )
    return True

def verify_otp(phone, otp_code, purpose="login"):
    """Verify an OTP code"""

    device = SMSDevice.objects.filter(phone_number=phone).first()
    if not device:
        return False

    with transaction.atomic():
        otp_objs = OTP.objects.filter(
            phone=phone,
            purpose=purpose,
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').select_for_update()

        if not otp_objs.exists():
            return False

        otp_obj = otp_objs.first()

        if not check_password(otp_code, otp_obj.hashed_code):
            return False

        otp_obj.is_used = True
        otp_obj.save()

        # Clear device token to prevent reuse
        device.current_token = ''
        device.token_timestamp = None
        device.save()

    return True