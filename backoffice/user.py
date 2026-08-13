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


from datetime import datetime

from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework.views import APIView
from db.models import UserMaster, CourtSport



class BackofficeDashboardApi(APIView):

    def get(self, request):

        try:
            from_date = request.GET.get("from_date")
            to_date = request.GET.get("to_date")

            # --------------------------------------------------
            # DATE VALIDATION
            # --------------------------------------------------

            from_date_obj = None
            to_date_obj = None

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

            if from_date_obj and to_date_obj:
                if from_date_obj > to_date_obj:
                    return CustomResponse.errorResponse(
                        description="from_date cannot be greater than to_date"
                    )

            # --------------------------------------------------
            # BOOKING DATE FILTER
            # --------------------------------------------------

            booking_filter = Q()

            if from_date_obj:
                booking_filter &= Q(
                    booking_date__gte=from_date_obj
                )

            if to_date_obj:
                booking_filter &= Q(
                    booking_date__lte=to_date_obj
                )

            bookings = Booking.objects.filter(
                booking_filter
            )

            # --------------------------------------------------
            # SUMMARY
            # --------------------------------------------------

            total_bookings = bookings.count()

            cancelled_bookings = bookings.filter(
                booking_status=Booking.STATUS_CANCELLED
            ).count()

            # --------------------------------------------------
            # REVENUE
            #
            # Only successful booking payments
            # --------------------------------------------------

            successful_payments = BookingPayment.objects.filter(
                booking__in=bookings,
                status=BookingPayment.STATUS_SUCCESS
            )

            total_revenue = (
                successful_payments.aggregate(
                    total=Sum("amount")
                )["total"] or 0
            )

            # BookingPayment.amount is currently stored in paise
            total_revenue = float(total_revenue) / 100

            # --------------------------------------------------
            # TOTAL USERS
            #
            # Date filter applies to user created_at
            # --------------------------------------------------

            users = UserMaster.objects.filter(
                is_active=True
            )

            if from_date_obj:
                users = users.filter(
                    created_at__date__gte=from_date_obj
                )

            if to_date_obj:
                users = users.filter(
                    created_at__date__lte=to_date_obj
                )

            total_users = users.count()

            # --------------------------------------------------
            # PAID USERS
            #
            # Unique users with successful booking payment
            # --------------------------------------------------

            paid_users = (
                successful_payments
                .values("booking__user_id")
                .distinct()
                .count()
            )

            # --------------------------------------------------
            # TOURNAMENTS HELD
            # --------------------------------------------------

            tournaments = Tournament.objects.filter(
                status=Tournament.STATUS_COMPLETED
            )

            if from_date_obj:
                tournaments = tournaments.filter(
                    tournament_date__gte=from_date_obj
                )

            if to_date_obj:
                tournaments = tournaments.filter(
                    tournament_date__lte=to_date_obj
                )

            tournaments_held = tournaments.count()

            # ==================================================
            # TODAY BOOKINGS
            # ==================================================

            today = timezone.localdate()

            today_bookings = (
                Booking.objects
                .filter(
                    booking_date=today,
                    booking_status__in=[
                        Booking.STATUS_CONFIRMED,
                        Booking.STATUS_COMPLETED
                    ]
                )
                .select_related(
                    "user",
                    "court"
                )
                .prefetch_related(
                    "slots"
                )
                .order_by(
                    "booking_date",
                    "created_at"
                )
            )

            # ==================================================
            # UPCOMING BOOKINGS
            # ==================================================

            upcoming_bookings = (
                Booking.objects
                .filter(
                    booking_date__gt=today,
                    booking_status=Booking.STATUS_CONFIRMED
                )
                .select_related(
                    "user",
                    "court"
                )
                .prefetch_related(
                    "slots"
                )
                .order_by(
                    "booking_date",
                    "created_at"
                )
            )

            # --------------------------------------------------
            # BOOKING RESPONSE HELPER
            # --------------------------------------------------

            def get_booking_data(booking):

                slots = booking.slots.all()

                return {
                    "id": str(booking.id),

                    "booking_number": booking.booking_number,

                    "user": {
                        "id": str(booking.user.id),
                        "name": booking.user.display_name,
                        "profile_image": booking.user.profile_image
                    },

                    "court": {
                        "id": str(booking.court.id),
                        "name": booking.court.name
                    },

                    "venue": {
                        "id": str(booking.court.venue.id),
                        "name": booking.court.venue.name
                    },

                    "booking_date": booking.booking_date,

                    "slots": [
                        {
                            "start_time": slot.start_time,
                            "end_time": slot.end_time,
                            "price": str(slot.price)
                        }
                        for slot in slots
                    ],

                    "total_amount": str(
                        booking.total_amount
                    ),

                    "payment_status": (
                        booking.payment_status
                    ),

                    "booking_status": (
                        booking.booking_status
                    )
                }

            today_data = [
                get_booking_data(booking)
                for booking in today_bookings
            ]

            upcoming_data = [
                get_booking_data(booking)
                for booking in upcoming_bookings
            ]

            # ==================================================
            # COURT STATISTICS
            # ==================================================

            court_statistics = (
                bookings
                .filter(
                    booking_status__in=[
                        Booking.STATUS_CONFIRMED,
                        Booking.STATUS_COMPLETED
                    ],
                    payment_status=Booking.PAYMENT_SUCCESS
                )
                .values(
                    "court_id",
                    "court__name"
                )
                .annotate(
                    booking_count=Count("id"),
                    total_amount=Sum("total_amount")
                )
                .order_by(
                    "-booking_count"
                )
            )

            court_data = []

            for item in court_statistics:

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

            # ==================================================
            # SPORT STATISTICS
            #
            # Booking does not directly have Sport.
            # We use CourtSport.
            # ==================================================

            sport_data = []

            court_sport_map = {}

            court_sports = (
                CourtSport.objects
                .filter(
                    is_active=True
                )
                .select_related(
                    "court",
                    "sport"
                )
            )

            for court_sport in court_sports:

                court_id = str(
                    court_sport.court_id
                )

                sport_data_for_court = court_sport_map.setdefault(
                    court_id,
                    []
                )

                sport_data_for_court.append({
                    "id": str(
                        court_sport.sport_id
                    ),
                    "name": court_sport.sport.name
                })

            # --------------------------------------------------
            # Aggregate bookings by sport
            # --------------------------------------------------

            sport_stats = {}

            valid_bookings = (
                bookings
                .filter(
                    booking_status__in=[
                        Booking.STATUS_CONFIRMED,
                        Booking.STATUS_COMPLETED
                    ],
                    payment_status=Booking.PAYMENT_SUCCESS
                )
                .select_related("court")
            )

            for booking in valid_bookings:

                court_id = str(
                    booking.court_id
                )

                sports = court_sport_map.get(
                    court_id,
                    []
                )

                # If a court has multiple sports,
                # the booking cannot be uniquely assigned
                # to one sport with the current DB structure.
                #
                # For now, use the first active sport.

                if not sports:
                    continue

                sport = sports[0]

                sport_id = sport["id"]

                if sport_id not in sport_stats:

                    sport_stats[sport_id] = {
                        "sport_id": sport_id,
                        "sport_name": sport["name"],
                        "booking_count": 0,
                        "amount": 0
                    }

                sport_stats[sport_id]["booking_count"] += 1

                sport_stats[sport_id]["amount"] += float(
                    booking.total_amount
                )

            sport_data = list(
                sport_stats.values()
            )

            for item in sport_data:
                item["amount"] = round(
                    item["amount"],
                    2
                )

            sport_data.sort(
                key=lambda x: x["booking_count"],
                reverse=True
            )

            # ==================================================
            # FINAL RESPONSE
            # ==================================================

            data = {

                "summary": {

                    "total_bookings": total_bookings,

                    "total_revenue": round(
                        total_revenue,
                        2
                    ),

                    "cancelled_bookings": cancelled_bookings,

                    "total_users": total_users,

                    "paid_users": paid_users,

                    "tournaments_held": tournaments_held
                },

                "bookings": {

                    "today": {
                        "count": len(today_data),
                        "data": today_data
                    },

                    "upcoming": {
                        "count": len(upcoming_data),
                        "data": upcoming_data
                    }
                },

                "court_statistics": court_data,

                "sport_statistics": sport_data
            }

            return CustomResponse.successResponse(
                data=data,
                description="Dashboard data fetched successfully"
            )

        except Exception as e:

            return CustomResponse.errorResponse(
                description=str(e)
            )


