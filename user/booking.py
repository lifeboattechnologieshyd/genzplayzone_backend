from datetime import datetime, timedelta

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import Court, Booking, BookingSlot, CourtPricing
from shared.utils import CustomResponse, check_slot_availability, calculate_booking_amount, generate_booking_number, \
    validate_booking_datetime, generate_slots


class BookingsApi(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        court_id = request.data.get("court_id")
        booking_date = request.data.get("booking_date")
        slots = request.data.get("slots", [])
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
                description="Please select at least one slot"
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
            validate_booking_datetime(booking_date,slots)
            check_slot_availability(court, booking_date,slots)
            total_amount, slot_prices = calculate_booking_amount(court, booking_date, slots)
            booking = Booking.objects.create(
                booking_number=generate_booking_number(),
                user=request.user,
                court=court,
                booking_date=booking_date,
                total_amount=total_amount,
                booking_status=Booking.STATUS_CONFIRMED,
            )
            for slot in slot_prices:
                BookingSlot.objects.create(
                    booking=booking,
                    start_time=slot["start_time"],
                    end_time=slot["end_time"],
                    price=slot["price"]
                )
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

    def get(self, request):
        booking_type = request.GET.get("type")
        bookings = Booking.objects.filter(
            user=request.user,
            is_active=True
        ).select_related(
            "court",
            "court__venue"
        ).prefetch_related(
            "slots"
        )
        today = timezone.localdate()
        if booking_type == "UPCOMING":
            bookings = bookings.filter(
                booking_date__gte=today,
                booking_status__in=[
                    Booking.STATUS_PENDING_PAYMENT,
                    Booking.STATUS_CONFIRMED
                ]
            )
        elif booking_type == "COMPLETED":
            bookings = bookings.filter(
                booking_status=Booking.STATUS_COMPLETED
            )
        elif booking_type == "CANCELLED":
            bookings = bookings.filter(
                booking_status=Booking.STATUS_CANCELLED
            )
        bookings = bookings.order_by(
            "-booking_date",
            "-created_at"
        )
        data = []
        for booking in bookings:
            slots = []
            for slot in booking.slots.all():
                slots.append({
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": slot.end_time.strftime("%H:%M")
                })
            data.append({
                "id": str(booking.id),
                "booking_number": booking.booking_number,
                "booking_date": booking.booking_date,
                "court": {
                    "id": str(booking.court.id),
                    "name": booking.court.name,
                    "cover_image": booking.court.cover_image
                },
                "venue": {
                    "id": str(booking.court.venue.id),
                    "name": booking.court.venue.name,
                    "address": booking.court.venue.address
                },
                "slots": slots,
                "total_amount": booking.total_amount,
                "booking_status": booking.booking_status,
                "payment_status": booking.payment_status
            })

        return CustomResponse().successResponse(
            data={
                "bookings": data
            },
            description="Bookings fetched successfully"
        )


from datetime import datetime

from django.db.models import Q
from django.utils import timezone


class CourtAvailabilityApi(APIView):
    permission_classes = [IsAuthenticated]


    def slot_status(self, booking_date, slot, booked):
        status = Booking.SLOT_STATUS_AVAILABLE
        if (slot["start_time"],slot["end_time"]) in booked:
            status = Booking.SLOT_STATUS_BOOKED
        else:
            today = timezone.localdate()
            if booking_date < today:
                status = Booking.SLOT_STATUS_PAST
            elif booking_date == today:
                booking_datetime = timezone.make_aware(
                    datetime.combine(
                        booking_date,
                        slot["start_time"]
                    )
                )
                if booking_datetime <= timezone.localtime() + timedelta(minutes=15):
                    status = Booking.SLOT_STATUS_PAST
        return status

    def get(self, request):
        court_id = request.GET.get("court_id")
        booking_date = request.GET.get("booking_date")
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
                description="Invalid booking date."
            )
        day = booking_date.strftime(
            "%A"
        ).upper()
        pricing_list = CourtPricing.objects.filter(
            court=court,
            day=day,
            is_active=True
        ).order_by(
            "start_time"
        )
        booked_slots = BookingSlot.objects.filter(
            booking__court=court,
            booking__booking_date=booking_date
        ).filter(
            Q(
                booking__booking_status=Booking.STATUS_CONFIRMED
            ) |
            Q(
                booking__booking_status=Booking.STATUS_PENDING_PAYMENT,
                booking__expires_at__gt=timezone.now()
            )
        )
        booked = set()
        for slot in booked_slots:
            booked.add(
                (
                    slot.start_time,
                    slot.end_time
                )
            )
        slots = []
        for pricing in pricing_list:
            generated_slots = generate_slots(
                pricing,
                court.slot_duration_minutes
            )
            for slot in generated_slots:
                available = (
                    slot["start_time"],
                    slot["end_time"]
                ) not in booked
                # Default
                status = self.slot_status(booking_date, slot, booked)

                slots.append({
                    "start_time": slot["start_time"].strftime("%H:%M"),
                    "end_time": slot["end_time"].strftime("%H:%M"),
                    "price": slot["price"],
                    "available": available,
                    "status": status
                })

        return CustomResponse().successResponse(
            data={
                "court": {
                    "id": str(court.id),
                    "name": court.name
                },
                "booking_date": booking_date,
                "slots": slots
            },
            description="Availability fetched successfully"
        )