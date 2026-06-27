from datetime import datetime

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import Court, Booking, BookingSlot
from shared.utils import CustomResponse, check_slot_availability, calculate_booking_amount, generate_booking_number, \
    validate_booking_datetime


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
                total_amount=total_amount
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