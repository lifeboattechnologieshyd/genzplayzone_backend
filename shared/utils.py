import random
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.utils.dateparse import parse_datetime
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from db.models import CourtPricing, Booking, BookingSlot
from db.models.promocode import PromoCode


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


def parse_promo_datetime(value, field_name):
    value = parse_datetime(value)

    if not value:
        raise Exception(f"Invalid {field_name}.")

    if timezone.is_naive(value):
        value = timezone.make_aware(value)

    return value


def parse_decimal(value, field_name, allow_zero=False):
    try:
        value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise Exception(f"Invalid {field_name}.")

    if value < 0 or (value == 0 and not allow_zero):
        raise Exception(f"{field_name} must be greater than zero.")

    return value

def get_promo_data(promo_code):
    return {
        "id": str(promo_code.id),
        "code": promo_code.code,
        "discount_amount": str(promo_code.discount_amount),
        "minimum_booking_amount": str(
            promo_code.minimum_booking_amount
        ),
        "valid_from": promo_code.valid_from,
        "valid_until": promo_code.valid_until,
        "total_usage_limit": promo_code.total_usage_limit,
        "per_user_usage_limit": promo_code.per_user_usage_limit,
        "is_active": promo_code.is_active,
    }


from django.db.models import Q
from django.utils import timezone

def get_promo_preview(promo_code_value, user, subtotal_amount):
    now = timezone.now()
    promo_code_value = promo_code_value.strip().upper()

    promo_code =  PromoCode.objects.filter(
        code=promo_code_value,
        is_active=True
    ).first()

    if not promo_code:
        raise Exception("Invalid or inactive promo code.")

    if promo_code.valid_from > now:
        raise Exception("This promo code is not active yet.")

    if promo_code.valid_until < now:
        raise Exception("This promo code has expired.")

    if subtotal_amount < promo_code.minimum_booking_amount:
        raise Exception(
            f"Minimum booking amount for this promo is "
            f"₹{promo_code.minimum_booking_amount}."
        )

    active_usage_filter = (
        Q(
            booking_status__in=[
                Booking.STATUS_CONFIRMED,
                Booking.STATUS_COMPLETED,
                Booking.STATUS_NO_SHOW,
            ]
        )
        |
        Q(
            booking_status=Booking.STATUS_PENDING_PAYMENT,
            expires_at__gt=now
        )
    )

    promo_bookings = Booking.objects.filter(
        promo_code=promo_code
    ).filter(active_usage_filter)

    if (
        promo_code.total_usage_limit is not None
        and promo_bookings.count() >= promo_code.total_usage_limit
    ):
        raise Exception("This promo code usage limit has been reached.")

    if (
        promo_code.per_user_usage_limit is not None
        and promo_bookings.filter(user=user).count()
        >= promo_code.per_user_usage_limit
    ):
        raise Exception(
            "You have already used this promo code the maximum number of times."
        )
    discount_amount = min(
        promo_code.discount_amount,
        subtotal_amount
    )
    return promo_code, discount_amount