from django.db import transaction
from django.utils import timezone

from db.models import Booking


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