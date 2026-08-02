import random
from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from db.models import UserMaster, OTPs, Booking
from shared.clients.sms import send_sms_to_mobile
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

        if "admin" not in roles:
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
        var = f"{otp}|"
        send_sms_to_mobile(var, mobile, 12558)
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

        if "admin" not in roles:
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


from django.db.models import Count, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class BackofficeDashboardApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")

        users = UserMaster.objects.all()

        bookings = Booking.objects.all()

        if from_date:
            users = users.filter(
                created_at__date__gte=from_date
            )
            bookings = bookings.filter(
                created_at__date__gte=from_date
            )

        if to_date:
            users = users.filter(
                created_at__date__lte=to_date
            )
            bookings = bookings.filter(
                created_at__date__lte=to_date
            )

        total_users = users.filter(
            user_role__contains=["user"]
        ).count()

        admins = users.filter(
            user_role__contains=["admin"]
        ).count()

        paid_users = 0
        # users.filter(
        #     booking__payment_status=Booking.PAYMENT_SUCCESS
        # ).distinct().count()

        total_bookings = bookings.count()

        upcoming_bookings = bookings.filter(
            booking_status=Booking.STATUS_CONFIRMED
        ).count()

        cancelled_bookings = bookings.filter(
            booking_status=Booking.STATUS_CANCELLED
        ).count()

        total_amount = bookings.filter(
            payment_status=Booking.PAYMENT_SUCCESS
        ).aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        cancelled_charges = bookings.filter(
            booking_status=Booking.STATUS_CANCELLED
        ).aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        return CustomResponse().successResponse(
            data={
                "users": {
                    "total_users": total_users,
                    "paid_users": paid_users,
                    "admins": admins
                },
                "bookings": {
                    "total_bookings": total_bookings,
                    "upcoming_bookings": upcoming_bookings,
                    "cancelled_bookings": cancelled_bookings
                },
                "revenue": {
                    "total_amount": total_amount,
                    "cancelled_charges": cancelled_charges
                }
            },
            description="Dashboard statistics fetched successfully"
        )