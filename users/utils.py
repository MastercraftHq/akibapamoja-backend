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
    try:
        current_count = cache.incr(count_key)
    except ValueError:
        cache.set(count_key, 1, timeout=window_seconds)
        current_count = 1

    if current_count > max_sends:
        raise OTPSendError("OTP request limit exceeded. Try again later.")

    user = None
    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        if purpose not in ["register", "phone_verification"]:
            logger.info(f"Fake OTP send for unregistered phone: {phone}")
            otp_code = generate_otp_code()
            cache.set(cooldown_key, True, timeout=cooldown_seconds)
            return otp_code

    # Create or get device
    device, created = SMSDevice.objects.get_or_create(
        phone_number=phone,
        defaults={'name': f"SMS Device for {phone}", 'user': user}
    )

    if not created and user and device.user != user:
        device.user = user
        device.save()

    # Generate OTP if not provided
    if otp_code is None:
        otp_code = generate_otp_code()
    
    # Hash once
    hashed_code = make_password(otp_code)
    
    device.current_token = hashed_code
    device.token_timestamp = timezone.now()
    device.save()

    success = device.send_token(token=otp_code)
    if not success:
        cache.decr(count_key)
        logger.error(f"Failed to send OTP to {phone}")
        raise OTPSendError("Unable to send OTP. Please try again.")
    
    # Set cooldown after successful send
    cache.set(cooldown_key, True, timeout=cooldown_seconds)
    
    with transaction.atomic():
        OTP.objects.filter(
            phone=phone,
            purpose=purpose,
            is_used=False,
            expires_at__gt=timezone.now()
        ).update(is_used=True)
        
        OTP.objects.create(
            phone=phone,
            hashed_code=hashed_code,
            purpose=purpose,
        )
    return otp_code

def verify_otp(phone, otp_code, purpose="login"):
    """Verify an OTP code"""

    verify_key = f"otp:verify:{phone}"
    max_attempts = 5
    window_seconds = 600

    with transaction.atomic():
        device = SMSDevice.objects.filter(phone_number=phone).select_for_update().first()

        # Rate limiting
        attempts = cache.get(verify_key, 0)
        attempts += 1
        cache.set(verify_key, attempts, timeout=window_seconds)

        verification_success = False

        otp_objs = OTP.objects.filter(
            phone=phone,
            purpose=purpose,
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').select_for_update()

        otp_obj = otp_objs.first() if otp_objs.exists() else None

        # Perform constant-time comparison even if no OTP
        dummy_hash = make_password("invalid")
        hash_to_check = otp_obj.hashed_code if otp_obj else dummy_hash

        if check_password(otp_code, hash_to_check) and otp_obj and attempts <= max_attempts and device:
            verification_success = True
            otp_obj.is_used = True
            otp_obj.save()

            # Clear device token to prevent reuse
            device.current_token = None
            device.token_timestamp = None
            device.save()

            cache.delete(verify_key)

    return verification_success