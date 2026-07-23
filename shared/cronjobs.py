from django.db import transaction
from django.utils import timezone

from db.models import Booking, BookingSlot


def expire_pending_bookings():
    now = timezone.now()

    with transaction.atomic():
        booking_ids = list(
            Booking.objects
            .select_for_update(skip_locked=True)
            .filter(
                booking_status=Booking.STATUS_PENDING_PAYMENT,
                expires_at__isnull=False,
                expires_at__lte=now,
            )
            .order_by("id")
            .values_list("id", flat=True)[:500]
        )
        if not booking_ids:
            return 0
        updated_count = Booking.objects.filter(
            id__in=booking_ids,
            booking_status=Booking.STATUS_PENDING_PAYMENT,
            expires_at__lte=now,
        ).update(
            booking_status=Booking.STATUS_EXPIRED,
            updated_at=now,
        )
    return updated_count
from datetime import datetime, timedelta

def mark_no_show_bookings():
    now = timezone.now()
    processed_booking_ids = set()
    no_show_count = 0
    # Fetch slots for confirmed bookings. Ordering ensures we use
    # the first slot when a booking contains multiple slots.
    booking_slots = (
        BookingSlot.objects
        .select_related("booking")
        .filter(
            booking__booking_status=Booking.STATUS_CONFIRMED,
            booking__booking_date__lte=now.date(),
        )
        .order_by("booking_id", "start_time")
    )

    for booking_slot in booking_slots:
        booking = booking_slot.booking

        # Ignore later slots in the same multi-slot booking.
        if booking.id in processed_booking_ids:
            continue

        processed_booking_ids.add(booking.id)

        slot_start = datetime.combine(
            booking.booking_date,
            booking_slot.start_time
        )

        slot_start = timezone.make_aware(
            slot_start,
            timezone.get_current_timezone()
        )

        no_show_after = slot_start + timedelta(hours=1)

        if now < no_show_after:
            continue

        # Avoid a race with check-in API.
        with transaction.atomic():
            locked_booking = (
                Booking.objects
                .select_for_update()
                .get(id=booking.id)
            )

            # If admin checked in while this cron was running,
            # do not change the booking.
            if locked_booking.booking_status != Booking.STATUS_CONFIRMED:
                continue

            locked_booking.booking_status = Booking.STATUS_NO_SHOW
            locked_booking.remarks = (
                f"{locked_booking.remarks or ''}\n"
                f"Automatically marked as no-show at "
                f"{timezone.localtime(now).strftime('%d %b %Y, %I:%M %p')}."
            )
            locked_booking.updated_at = now
            locked_booking.save(
                update_fields=[
                    "booking_status",
                    "remarks",
                    "updated_at",
                ]
            )
            no_show_count += 1
    return no_show_count