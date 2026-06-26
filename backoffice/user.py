import random
from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from db.models import UserMaster, OTPs
from shared.clients.sms import send_otp_sms
from shared.utils import CustomResponse


class MobileSendOTPAdminView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        mobile = request.data.get("mobile")

        if not mobile:
            return CustomResponse().errorResponse(
                description="Mobile number is required",
            )

        # Get user
        user = UserMaster.objects.filter(mobile=mobile).first()

        if not user:
            return CustomResponse().errorResponse(
                description="User not found"
            )

        #  Check role
        roles = user.user_role or []

        if "ADMIN" not in roles:
            return CustomResponse().errorResponse(
                description="Access denied. Not an admin"
            )
        otp = str(random.randint(1000, 9999))
        expires_at = timezone.now() + timedelta(minutes=15)
        OTPs.objects.filter(
            mobile_number=mobile,
            is_active=True
        ).update(is_active=False)
        OTPs.objects.create(
            mobile_number=mobile,
            otp=otp,
            expires_at=expires_at,
            is_active=True
        )
        send_otp_sms(mobile, otp)
        return CustomResponse().successResponse(
            description="OTP sent successfully",
            data={
                "mobile": mobile,
                "otp": otp,
            }
        )

class MobileVerifyOTPAdminView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        mobile = request.data.get("mobile")
        otp = request.data.get("otp")
        if not mobile or not otp:
            return CustomResponse().errorResponse(
                description="Mobile and OTP are required",
            )

        user = UserMaster.objects.filter(mobile=mobile).first()
        if not user:
            return CustomResponse().errorResponse(
                description="User not found"
            )
        #  Check role
        roles = user.user_role or []

        if "ADMIN" not in roles:
            return CustomResponse().errorResponse(
                description="Access denied. Not an admin"
            )

        otp_obj = (
            OTPs.objects
            .filter(mobile_number=mobile, otp=otp, is_active=True)
            .order_by("-expires_at")
            .first()
        )

        if not otp_obj:
            return CustomResponse().errorResponse(
                description="Invalid OTP",
            )

        if timezone.now() > otp_obj.expires_at:
            return CustomResponse().errorResponse(
                description="OTP has expired",
            )
        otp_obj.is_active = False
        otp_obj.save(update_fields=["is_active"])
        user = UserMaster.objects.filter(mobile=mobile).first()
        user.last_login = timezone.now()
        user.save()
        refresh = RefreshToken.for_user(user)

        return CustomResponse().successResponse(
            description="OTP verified successfully",
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )
