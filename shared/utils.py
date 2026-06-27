import random
from datetime import datetime

from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from db.models import CourtPricing, Booking, BookingSlot


def getReferralCode():
    return f"GENZ{random.randint(10000, 99999)}"


class CustomResponse:

    @staticmethod
    def successResponse(
        data, errorCode=0, description="Request Successful", total=0, status=status.HTTP_200_OK, **kwargs
    ):
        return Response(
            {
                "success": True,
                "errorCode": errorCode,
                "description": description,
                "total": total,
                **kwargs,
                "data": data,
            },
            status=status,
        )

    @staticmethod
    def errorResponse(
        data=None,
        errorCode=0,
        description="Request Failed",
        total=0,
        status=status.HTTP_200_OK,
        **kwargs,
    ):
        if data is None:
            data = {}
        return Response(
            {
                "success": False,
                "errorCode": errorCode,
                "description": description,
                "total": total,
                "data": data,
                **kwargs,
            },
            status=status,
        )


from django.db.models import Min

def update_starting_price(court):
    lowest_price = CourtPricing.objects.filter(
        court=court,
        is_active=True
    ).aggregate(
        Min("price")
    )
    court.starting_price = lowest_price["price__min"] or 0
    court.save(update_fields=["starting_price"])


def generate_booking_number():
    last_booking = Booking.objects.order_by(
        "-created_at"
    ).first()
    if not last_booking:
        return "GPZ000001"
    try:
        last_number = int(
            last_booking.booking_number.replace(
                "GPZ",
                ""
            )
        )
    except Exception:
        last_number = 0
    return f"GPZ{last_number + 1:06d}"

def calculate_booking_amount(court, booking_date, slots):
    day = booking_date.strftime(
        "%A"
    ).upper()
    total_amount = 0
    slot_prices = []
    for slot in slots:
        start_time = datetime.strptime(
            slot["start_time"],
            "%H:%M"
        ).time()

        end_time = datetime.strptime(
            slot["end_time"],
            "%H:%M"
        ).time()
        pricing = CourtPricing.objects.filter(
            court=court,
            day=day,
            is_active=True,
            start_time__lte=start_time,
            end_time__gte=end_time
        ).first()

        if not pricing:
            raise Exception(
                f"No pricing configured for {slot['start_time']} - {slot['end_time']}"
            )
        total_amount += pricing.price
        slot_prices.append({
            "start_time": start_time,
            "end_time": end_time,
            "price": pricing.price
        })
    return total_amount, slot_prices



def check_slot_availability(court,booking_date,slots):
    for slot in slots:
        exists = BookingSlot.objects.filter(
            booking__court=court,
            booking__booking_date=booking_date,
            booking__booking_status__in=[
                Booking.STATUS_PENDING_PAYMENT,
                Booking.STATUS_CONFIRMED
            ],
            start_time=slot["start_time"],
            end_time=slot["end_time"]
        ).exists()
        if exists:
            raise Exception(
                f"{slot['start_time']} - {slot['end_time']} already booked."
            )

def validate_booking_datetime(booking_date,slots):
    """
    Raises Exception if booking is for a past date/time.
    """
    now = timezone.localtime()
    today = now.date()
    if booking_date < today:
        raise Exception(
            "Booking date cannot be in the past."
        )
    if booking_date > today:
        return
    current_time = now.time()
    for slot in slots:
        slot_start = datetime.strptime(
            slot["start_time"],
            "%H:%M"
        ).time()
        if slot_start <= current_time:
            raise Exception(
                f"{slot['start_time']} slot has already started."
            )


from datetime import datetime, timedelta


def generate_slots(pricing, slot_duration):
    slots = []
    current = datetime.combine(
        datetime.today(),
        pricing.start_time
    )
    end = datetime.combine(
        datetime.today(),
        pricing.end_time
    )

    while current < end:

        next_slot = current + timedelta(
            minutes=slot_duration
        )

        if next_slot > end:
            break

        slots.append({
            "start_time": current.time(),
            "end_time": next_slot.time(),
            "price": pricing.price
        })
        current = next_slot
    return slots