from django.db import models
from db.models import AuditModel


class PromoCode(AuditModel):
    code = models.CharField(
        max_length=50,
        unique=True
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    minimum_booking_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()

    total_usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    per_user_usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "promo_codes"