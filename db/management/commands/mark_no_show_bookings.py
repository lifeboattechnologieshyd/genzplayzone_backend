from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from datetime import datetime, timedelta

from db.models import Booking, BookingSlot


class Command(BaseCommand):
    help = "Mark confirmed bookings as NO_SHOW if not checked in within 1 hour after slot start."

    def handle(self, *args, **options):
        with open("/tmp/no_show_cron_test.log", "a") as f:
            f.write(f"No-show cron executed at {timezone.now()}\n")

        print("=" * 60)
        print("Mark No-Show Bookings Cron Started")
        print("=" * 60)

        now = timezone.now()
        print(f"Current Time: {now}")

        try:
            processed_booking_ids = set()
            no_show_count = 0

            print("Fetching confirmed booking slots...")

            booking_slots = (
                BookingSlot.objects
                .select_related("booking")
                .filter(
                    booking__booking_status=Booking.STATUS_CONFIRMED,
                    booking__booking_date__lte=now.date(),
                )
                .order_by("booking_id", "start_time")
            )

            print(f"Total Booking Slots Found: {booking_slots.count()}")

            for booking_slot in booking_slots:
                booking = booking_slot.booking

                # Skip duplicate bookings having multiple slots
                if booking.id in processed_booking_ids:
                    continue

                processed_booking_ids.add(booking.id)

                slot_start = datetime.combine(
                    booking.booking_date,
                    booking_slot.start_time,
                )

                slot_start = timezone.make_aware(
                    slot_start,
                    timezone.get_current_timezone(),
                )

                no_show_after = slot_start + timedelta(hours=1)

                if now < no_show_after:
                    print(
                        f"Skipping Booking #{booking.id} - "
                        f"1 hour grace period not completed."
                    )
                    continue

                with transaction.atomic():
                    locked_booking = (
                        Booking.objects
                        .select_for_update()
                        .get(id=booking.id)
                    )

                    # Booking may have been checked in while cron was running
                    if locked_booking.booking_status != Booking.STATUS_CONFIRMED:
                        print(
                            f"Skipping Booking #{locked_booking.id} - "
                            f"Status changed to {locked_booking.booking_status}"
                        )
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
                    print(f"Booking #{locked_booking.id} marked as NO_SHOW.")

            print("=" * 60)
            print(f"Total Bookings Marked as NO_SHOW: {no_show_count}")
            print("Cron completed successfully.")
            print("=" * 60)

        except Exception as e:
            print(f"Error while marking no-show bookings: {e}")
            raise