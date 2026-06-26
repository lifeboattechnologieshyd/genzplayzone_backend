from db.models import AuditModel
from django.db import models


class Venue(AuditModel):
    name = models.CharField(
        max_length=255
    )
    address = models.TextField(
        blank=True,
        null=True
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )
    cover_image = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    contact_number = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )
    description = models.TextField(
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        default=True
    )
    class Meta:
        db_table = "venues"



class Amenity(AuditModel):

    name = models.CharField(
        max_length=100,
        unique=True
    )
    icon = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )
    description = models.TextField(
        blank=True,
        null=True
    )
    display_order = models.PositiveIntegerField(
        default=0
    )
    is_active = models.BooleanField(
        default=True
    )
    class Meta:
        db_table = "amenities"
        ordering = [
            "display_order",
            "name"
        ]
    def __str__(self):
        return self.name


class VenueAmenity(AuditModel):

    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="amenities"
    )
    amenity = models.ForeignKey(
        Amenity,
        on_delete=models.CASCADE,
        related_name="venues"
    )
    is_active = models.BooleanField(
        default=True
    )
    class Meta:
        db_table = "venue_amenities"
        unique_together = (
            "venue",
            "amenity"
        )
    def __str__(self):
        return f"{self.venue.name} - {self.amenity.name}"