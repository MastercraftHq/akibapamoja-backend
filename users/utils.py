from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password, make_password
from django.conf import settings
from users.models import OTP, SMSDevice
from .exceptions import OTPSendError
import secrets
import logging

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

    device, _ = SMSDevice.objects.get_or_create(
        phone_number=phone,
        defaults={'name': f"SMS Device for {phone}"}
    )

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
        logger.error(f"Failed to send OTP to {phone}")
        raise OTPSendError("Failed to send OTP. Please try again.")
    
    # Create OTP record with hashed code for consistency
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

    if not device.verify_token(otp_code):
        return False

    # Mark corresponding OTP as used (if exists)
    otp_objs = OTP.objects.filter(
        phone=phone,
        purpose=purpose,
        is_used=False,
        expires_at__gt=timezone.now()
    ).order_by('-created_at')
    if otp_objs.exists():
        otp_obj = otp_objs.first()
        otp_obj.is_used = True
        otp_obj.save()

    return True