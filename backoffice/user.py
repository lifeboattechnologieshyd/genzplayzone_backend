import random
from datetime import timedelta, datetime

from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from db.models import UserMaster, OTPs, Booking, BookingPayment, Tournament
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


from django.db.models import Count, Sum, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class BackofficeDashboardApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        try:

            from_date = request.GET.get("from_date")
            to_date = request.GET.get("to_date")

            # --------------------------------------------------
            # DATE FILTER
            # --------------------------------------------------

            date_filter = Q()

            if from_date:

                try:
                    from_date_obj = datetime.strptime(
                        from_date,
                        "%Y-%m-%d"
                    ).date()

                except ValueError:

                    return CustomResponse.errorResponse(
                        description="Invalid from_date. Use YYYY-MM-DD"
                    )

                date_filter &= Q(
                    booking_date__gte=from_date_obj
                )

            if to_date:

                try:
                    to_date_obj = datetime.strptime(
                        to_date,
                        "%Y-%m-%d"
                    ).date()

                except ValueError:

                    return CustomResponse.errorResponse(
                        description="Invalid to_date. Use YYYY-MM-DD"
                    )

                date_filter &= Q(
                    booking_date__lte=to_date_obj
                )

            # --------------------------------------------------
            # BOOKINGS
            # --------------------------------------------------

            bookings = Booking.objects.filter(
                date_filter
            )

            total_bookings = bookings.count()

            cancelled_bookings = bookings.filter(
                status=Booking.STATUS_CANCELLED
            ).count()

            # --------------------------------------------------
            # REVENUE
            # --------------------------------------------------

            booking_payments = BookingPayment.objects.filter(
                booking__in=bookings,
                status=BookingPayment.STATUS_SUCCESS
            )

            revenue = (
                booking_payments.aggregate(
                    total=Sum("amount")
                )["total"] or 0
            )

            # If BookingPayment.amount is stored in paise
            revenue = float(revenue) / 100

            # --------------------------------------------------
            # TOTAL USERS
            # --------------------------------------------------

            users = UserMaster.objects.filter(
                is_active=True
            )

            if from_date or to_date:

                user_date_filter = Q()

                if from_date:
                    user_date_filter &= Q(
                        created_at__date__gte=from_date_obj
                    )

                if to_date:
                    user_date_filter &= Q(
                        created_at__date__lte=to_date_obj
                    )

                users = users.filter(
                    user_date_filter
                )

            total_users = users.count()

            # --------------------------------------------------
            # PAID USERS
            # --------------------------------------------------
            paid_users = (
                booking_payments
                .values("booking__user")
                .distinct()
                .count()
            )

            # --------------------------------------------------
            # TOURNAMENTS HELD
            # --------------------------------------------------

            tournaments = Tournament.objects.filter(
                status=Tournament.STATUS_COMPLETED
            )
            if from_date:

                tournaments = tournaments.filter(
                    tournament_date__gte=from_date_obj
                )

            if to_date:

                tournaments = tournaments.filter(
                    tournament_date__lte=to_date_obj
                )

            tournaments_held = tournaments.count()

            # --------------------------------------------------
            # TODAY / UPCOMING BOOKINGS
            # --------------------------------------------------

            today = timezone.localdate()

            today_bookings = (
                Booking.objects
                .filter(
                    booking_date=today
                )
                .select_related(
                    "user",
                    "court",
                    "sport"
                )
                .order_by(
                    "start_time"
                )
            )

            upcoming_bookings = (
                Booking.objects
                .filter(
                    booking_date__gt=today
                )
                .select_related(
                    "user",
                    "court",
                    "sport"
                )
                .order_by(
                    "booking_date",
                    "start_time"
                )
            )

            # --------------------------------------------------
            # BOOKING SERIALIZER
            # --------------------------------------------------

            def booking_data(booking):

                return {
                    "id": str(booking.id),
                    "booking_number": booking.booking_number,

                    "user": {
                        "id": str(booking.user.id),
                        "name": booking.user.display_name,
                        "profile_image": booking.user.profile_image,
                    },

                    "court": {
                        "id": str(booking.court.id),
                        "name": booking.court.name,
                    },

                    "sport": {
                        "id": str(booking.sport.id),
                        "name": booking.sport.name,
                    },

                    "booking_date": booking.booking_date,
                    "start_time": booking.start_time,
                    "end_time": booking.end_time,

                    "amount": str(booking.amount),

                    "status": booking.status,
                }

            today_data = [
                booking_data(booking)
                for booking in today_bookings
            ]

            upcoming_data = [
                booking_data(booking)
                for booking in upcoming_bookings
            ]

            # --------------------------------------------------
            # COURT SPECIFIC BOOKINGS
            # --------------------------------------------------

            court_data = []

            court_stats = (
                bookings
                .values(
                    "court_id",
                    "court__name"
                )
                .annotate(
                    booking_count=Count("id"),
                    total_amount=Sum("amount")
                )
                .order_by(
                    "-booking_count"
                )
            )

            for item in court_stats:

                court_data.append({
                    "court_id": str(
                        item["court_id"]
                    ),

                    "court_name": item["court__name"],

                    "booking_count": item["booking_count"],

                    "amount": str(
                        item["total_amount"] or 0
                    )
                })

            # --------------------------------------------------
            # SPORT SPECIFIC BOOKINGS
            # --------------------------------------------------

            sport_data = []

            sport_stats = (
                bookings
                .values(
                    "sport_id",
                    "sport__name"
                )
                .annotate(
                    booking_count=Count("id"),
                    total_amount=Sum("amount")
                )
                .order_by(
                    "-booking_count"
                )
            )

            for item in sport_stats:

                sport_data.append({
                    "sport_id": str(
                        item["sport_id"]
                    ),

                    "sport_name": item["sport__name"],

                    "booking_count": item["booking_count"],

                    "amount": str(
                        item["total_amount"] or 0
                    )
                })

            # --------------------------------------------------
            # FINAL RESPONSE
            # --------------------------------------------------

            data = {

                # ==========================================
                # DASHBOARD SUMMARY
                # ==========================================

                "summary": {

                    "total_bookings":
                        total_bookings,

                    "total_revenue":
                        round(revenue, 2),

                    "cancelled_bookings":
                        cancelled_bookings,

                    "total_users":
                        total_users,

                    "paid_users":
                        paid_users,

                    "tournaments_held":
                        tournaments_held,
                },

                # ==========================================
                # TODAY / UPCOMING
                # ==========================================

                "bookings": {

                    "today": {
                        "count": len(today_data),
                        "data": today_data,
                    },

                    "upcoming": {
                        "count": len(upcoming_data),
                        "data": upcoming_data,
                    }
                },

                # ==========================================
                # COURTS
                # ==========================================

                "court_statistics": court_data,

                # ==========================================
                # SPORTS
                # ==========================================

                "sport_statistics": sport_data,
            }

            return CustomResponse.successResponse(
                data=data,
                description="Dashboard data fetched successfully"
            )

        except Exception as e:

            return CustomResponse.errorResponse(
                description=str(e)
            )