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
    STATUS_EXPIRED = "EXPIRED"

    STATUS_NO_SHOW = "NO_SHOW"
    BOOKING_STATUS_CHOICES = (
        (STATUS_PENDING_PAYMENT, "Pending Payment"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_EXPIRED, "Expired"),
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

    REFUND_NOT_APPLICABLE = "NOT_APPLICABLE"
    REFUND_PENDING = "PENDING"
    REFUND_SUCCESS = "SUCCESS"
    REFUND_FAILED = "FAILED"

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
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        UserMaster,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cancelled_bookings"
    )
    cancellation_reason = models.TextField(blank=True, null=True)
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    refund_status = models.CharField(
        max_length=30,
        default=REFUND_NOT_APPLICABLE
    )

    class Meta:
        db_table = "bookings"
        ordering = [
            "-created_at"
        ]
        indexes = [
            models.Index(
                fields=["court", "booking_date", "booking_status"]
            ),
            models.Index(
                fields=["booking_status", "expires_at"]
            ),
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


class BookingQRCode(AuditModel):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="qr_code"
    )
    token = models.CharField(max_length=128, unique=True)
    is_used = models.BooleanField(default=False)
    generated_at = models.DateTimeField(auto_now_add=True)
    scanned_at = models.DateTimeField(null=True, blank=True)
    scanned_by = models.ForeignKey(
        UserMaster,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        db_table = "booking_qrcode"

    def __str__(self):
        return f"{self.token}"


import uuid

class BookingPayment(AuditModel):

    STATUS_PENDING = "PENDING"
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILED = "FAILED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_EXPIRED = "EXPIRED"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
    )
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="payment"
    )
    payment_gateway = models.CharField(
        max_length=50,
        default="PHONEPE"
    )
    order_id = models.CharField(
        max_length=100,
        unique=True
    )
    transaction_id = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    raw_response = models.JSONField(
        blank=True,
        null=True
    )
    paid_at = models.DateTimeField(
        blank=True,
        null=True
    )
    def __str__(self):
        return self.order_id

