from django.core.management import BaseCommand
from django.db import transaction
from django.utils import timezone

from db.models import Booking

class Command(BaseCommand):
    help = "Expire pending bookings"

    def handle(self, *args, **options):
        print("=" * 60)
        print("Expire Pending Bookings Cron Started")
        print("=" * 60)

        now = timezone.now()
        print(f"Current Time: {now}")

        try:
            with transaction.atomic():
                print("Fetching expired pending bookings...")

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

                print(f"Booking IDs Found: {booking_ids}")
                print(f"Total Bookings Found: {len(booking_ids)}")

                if not booking_ids:
                    print("No pending bookings found to expire.")
                    return

                print("Updating booking status to EXPIRED...")

                updated_count = Booking.objects.filter(
                    id__in=booking_ids,
                    booking_status=Booking.STATUS_PENDING_PAYMENT,
                    expires_at__lte=now,
                ).update(
                    booking_status=Booking.STATUS_EXPIRED,
                    updated_at=now,
                )

                print(f"Updated Rows Count: {updated_count}")

            print("Transaction committed successfully.")
            print("Cron completed successfully.")

        except Exception as e:
            print(f"Error while expiring bookings: {e}")
            raise