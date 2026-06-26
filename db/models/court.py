import uuid

from django.db import models

from db.models import AuditModel, Venue, Sport


class Court(AuditModel):
    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="courts"
    )
    name = models.CharField(
        max_length=255
    )
    description = models.TextField(
        null=True,
        blank=True
    )
    cover_image = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )
    slot_duration_minutes = models.PositiveIntegerField(
        default=60
    )
    max_players = models.PositiveIntegerField(
        default=0
    )
    display_order = models.PositiveIntegerField(
        default=0
    )
    is_active = models.BooleanField(
        default=True
    )
    avg_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )
    reviews_count = models.PositiveIntegerField(
        default=0
    )
    starting_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    class Meta:
        db_table = "courts"
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class CourtSport(AuditModel):
    court = models.ForeignKey(
        Court,
        on_delete=models.CASCADE,
        related_name="court_sports"
    )
    sport = models.ForeignKey(
        Sport,
        on_delete=models.CASCADE,
        related_name="sport_courts"
    )
    is_active = models.BooleanField(
        default=True
    )
    class Meta:
        db_table = "court_sports"
        unique_together = (
            "court",
            "sport"
        )

class CourtMedia(AuditModel):
    court = models.ForeignKey(
        Court,
        on_delete=models.CASCADE,
        related_name="media"
    )
    image = models.CharField(
        max_length=500
    )
    display_order = models.PositiveIntegerField(
        default=0
    )
    is_active = models.BooleanField(
        default=True
    )
    class Meta:
        db_table = "court_media"
        ordering = ["display_order"]


class CourtPricing(AuditModel):

    court = models.ForeignKey(
        Court,
        on_delete=models.CASCADE,
        related_name="pricing"
    )

    day = models.CharField(
        max_length=20,
        choices=(
            ("MONDAY", "MONDAY"),
            ("TUESDAY", "TUESDAY"),
            ("WEDNESDAY", "WEDNESDAY"),
            ("THURSDAY", "THURSDAY"),
            ("FRIDAY", "FRIDAY"),
            ("SATURDAY", "SATURDAY"),
            ("SUNDAY", "SUNDAY"),
        )
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        db_table = "court_pricing"
        ordering = [
            "court",
            "day",
            "start_time"
        ]

class CourtPricingOverride(AuditModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    court = models.ForeignKey(
        Court,
        on_delete=models.CASCADE,
        related_name="pricing_overrides"
    )
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    reason = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        default=True
    )
    class Meta:
        db_table = "court_pricing_overrides"