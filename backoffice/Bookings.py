from datetime import datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from db.models import Booking, BookingPayment, BookingSlot, Court, UserMaster
from shared.clients.sms import send_sms_to_mobile
from shared.utils import CustomResponse, generate_booking_number, calculate_booking_amount, check_slot_availability, \
    validate_booking_datetime


class BackofficeBookingListApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search = request.GET.get("search")
        booking_status = request.GET.get("booking_status")
        payment_status = request.GET.get("payment_status")
        venue_id = request.GET.get("venue_id")
        court_id = request.GET.get("court_id")
        booking_date = request.GET.get("booking_date")
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")
        bookings = (
            Booking.objects
            .select_related(
                "user",
                "court",
                "court__venue",
            ).prefetch_related(
                "slots",
                "court__court_sports",
                "court__court_sports__sport"
            )
            .order_by("-created_at")
        )
        if search:
            bookings = bookings.filter(
                Q(booking_number__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__phone__icontains=search)
            )
        if booking_status:
            bookings = bookings.filter(
                booking_status=booking_status
            )
        if payment_status:
            bookings = bookings.filter(
                payment_status=payment_status
            )
        if venue_id:
            bookings = bookings.filter(
                court__venue_id=venue_id
            )
        if court_id:
            bookings = bookings.filter(
                court_id=court_id
            )
        if booking_date:
            bookings = bookings.filter(
                booking_date=booking_date
            )
        if from_date:
            bookings = bookings.filter(
                booking_date__gte=from_date
            )
        if to_date:
            bookings = bookings.filter(
                booking_date__lte=to_date
            )
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 20))
        start = (page - 1) * page_size
        end = start + page_size
        total_count = bookings.count()
        bookings = bookings[start:end]
        data = []
        for booking in bookings:
            slot_data = []
            for slot in booking.slots.all():
                slot_data.append({
                    "start_time": slot.start_time.strftime("%I:%M %p"),
                    "end_time": slot.end_time.strftime("%I:%M %p"),
                    "price": float(slot.price)
                })
            sports = [
                cs.sport.name
                for cs in booking.court.court_sports.filter(is_active=True)
            ]
            data.append({
                "booking_id": str(booking.id),
                "booking_number": booking.booking_number,
                "customer_name": booking.user.full_name,
                "customer_mobile": booking.user.mobile,
                "venue": booking.court.venue.name,
                "court": booking.court.name,
                "sports": sports,
                "booking_date": booking.booking_date,
                "slots": slot_data,
                "total_amount": float(booking.total_amount),
                "booking_status": booking.booking_status,
                "payment_status": booking.payment_status,
                "created_at": booking.created_at
            })
        return CustomResponse().successResponse(
            data={
                "count": total_count,
                "page": page,
                "page_size": page_size,
                "results": data
            },
            description="Bookings fetched successfully"
        )


    @transaction.atomic
    def post(self, request):

        user_id = request.data.get("user_id")
        court_id = request.data.get("court_id")
        booking_date = request.data.get("booking_date")
        slots = request.data.get("slots", [])
        payment_method = request.data.get("payment_method", "CASH")

        if not user_id:
            return CustomResponse().errorResponse(
                data={},
                description="User is required"
            )

        if not court_id:
            return CustomResponse().errorResponse(
                data={},
                description="Court is required"
            )

        if not booking_date:
            return CustomResponse().errorResponse(
                data={},
                description="Booking date is required"
            )

        if not slots:
            return CustomResponse().errorResponse(
                data={},
                description="Please select slots"
            )

        try:
            user = UserMaster.objects.get(
                id=user_id,
                is_active=True
            )
        except UserMaster.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="User not found"
            )

        try:
            court = Court.objects.get(
                id=court_id,
                is_active=True
            )
        except Court.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Court not found"
            )

        try:
            booking_date = datetime.strptime(
                booking_date,
                "%Y-%m-%d"
            ).date()
        except Exception:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid booking date"
            )
        try:
            validate_booking_datetime(
                booking_date,
                slots
            )

            check_slot_availability(
                court,
                booking_date,
                slots
            )

            total_amount, slot_prices = calculate_booking_amount(
                court,
                booking_date,
                slots
            )

            booking = Booking.objects.create(
                booking_number=generate_booking_number(),
                user=user,
                court=court,
                booking_date=booking_date,
                total_amount=total_amount,
                booking_status=Booking.STATUS_CONFIRMED,
                payment_status=Booking.PAYMENT_SUCCESS
            )

            for slot in slot_prices:

                BookingSlot.objects.create(
                    booking=booking,
                    start_time=slot["start_time"],
                    end_time=slot["end_time"],
                    price=slot["price"]
                )

            BookingPayment.objects.create(
                booking=booking,
                payment_gateway=payment_method,
                order_id=f"OFFLINE-{booking.booking_number}",
                amount=booking.total_amount,
                status=BookingPayment.STATUS_SUCCESS,
                paid_at=timezone.now(),
                raw_response={
                    "created_by": str(request.user.id),
                    "type": "BACKOFFICE"
                }
            )

            first_slot = BookingSlot.objects.filter(booking=booking).order_by("start_time").first()

            start_time = first_slot.start_time.strftime("%-I %p")
            end_time = first_slot.end_time.strftime("%-I %p")

            slot_text = (
                f"{booking.booking_date.strftime('%d %b %Y')}, "
                f"{start_time}-{end_time}"
            )
            # TODO: send push and email n whatsapp too.
            username = "Player" if user.full_name is None else user.full_name
            var = f"{username}|{booking.booking_number}|{booking.court.name}|{slot_text}|"
            print(var)
            send_sms_to_mobile(var, user.mobile, 12663)
            print("SMS Sent successfully")
            # send_push_notification()
            # send_whatsapp()
            # send_email()

            return CustomResponse().successResponse(
                data={
                    "booking_id": str(booking.id),
                    "booking_number": booking.booking_number,
                    "total_amount": booking.total_amount
                },
                description="Booking created successfully"
            )

        except Exception as e:
            return CustomResponse().errorResponse(
                data={},
                description=str(e)
            )


