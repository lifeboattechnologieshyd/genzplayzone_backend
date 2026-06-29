from django.db import models
from db.models import AuditModel, UserMaster, Court


class Booking(AuditModel):
    SLOT_STATUS_AVAILABLE = "AVAILABLE"
    SLOT_STATUS_BOOKED = "BOOKED"
    SLOT_STATUS_PAST = "PAST"
    SLOT_STATUS_BLOCKED = "BLOCKED"
    SLOT_STATUS_MAINTENANCE = "MAINTENANCE"

    STATUS_PENDING_PAYMENT = "PENDING_PAYMENT"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_NO_SHOW = "NO_SHOW"
    BOOKING_STATUS_CHOICES = (
        (STATUS_PENDING_PAYMENT, "Pending Payment"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_NO_SHOW, "No Show"),
    )
    PAYMENT_PENDING = "PENDING"
    PAYMENT_SUCCESS = "SUCCESS"
    PAYMENT_FAILED = "FAILED"
    PAYMENT_REFUNDED = "REFUNDED"
    PAYMENT_STATUS_CHOICES = (
        (PAYMENT_PENDING, "Pending"),
        (PAYMENT_SUCCESS, "Success"),
        (PAYMENT_FAILED, "Failed"),
        (PAYMENT_REFUNDED, "Refunded"),
    )

    booking_number = models.CharField(
        max_length=20,
        unique=True
    )

    user = models.ForeignKey(
        UserMaster,
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    court = models.ForeignKey(
        Court,
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    booking_date = models.DateField()

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_PENDING
    )
    booking_status = models.CharField(
        max_length=30,
        choices=BOOKING_STATUS_CHOICES,
        default=STATUS_PENDING_PAYMENT
    )

    payment_reference = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    remarks = models.TextField(
        blank=True,
        null=True
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )
    class Meta:
        db_table = "bookings"
        ordering = [
            "-created_at"
        ]

    def __str__(self):
        return self.booking_number

class BookingSlot(AuditModel):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="slots"
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        db_table = "booking_slots"
        ordering = [
            "start_time"
        ]

    def __str__(self):
        return f"{self.booking} - {self.start_time} - {self.end_time}"