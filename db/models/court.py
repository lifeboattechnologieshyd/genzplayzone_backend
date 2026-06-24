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
    class Meta:
        db_table = "courts"
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name

import uuid

from django.db import models

from db.models import AuditModel, Venue


class Court(AuditModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
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