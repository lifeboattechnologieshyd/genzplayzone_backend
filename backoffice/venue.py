
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import Venue, Amenity, VenueAmenity
from shared.utils import CustomResponse


class VenuesApi(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        name = request.data.get("name")
        address = request.data.get("address")
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        cover_image = request.data.get("cover_image")
        opening_time = request.data.get("opening_time")
        closing_time = request.data.get("closing_time")
        contact_number = request.data.get("contact_number")
        description = request.data.get("description")

        if not name:
            return CustomResponse().errorResponse(
                data={},
                description="Venue name is required"
            )

        venue = Venue.objects.create(
            name=name,
            address=address,
            latitude=latitude,
            longitude=longitude,
            cover_image=cover_image,
            opening_time=opening_time,
            closing_time=closing_time,
            contact_number=contact_number,
            description=description
        )

        return CustomResponse().successResponse(
            data={
                "id": str(venue.id)
            },
            description="Venue created successfully"
        )

    def get(self, request):

        search = request.GET.get("search")

        venues = Venue.objects.filter(
            is_active=True
        )

        if search:
            venues = venues.filter(
                name__icontains=search
            )

        data = []

        for venue in venues:
            data.append({
                "id": str(venue.id),
                "name": venue.name,
                "address": venue.address,
                "latitude": venue.latitude,
                "longitude": venue.longitude,
                "cover_image": venue.cover_image,
                "opening_time": venue.opening_time,
                "closing_time": venue.closing_time,
                "contact_number": venue.contact_number,
                "description": venue.description,
            })

        return CustomResponse().successResponse(
            data={
                "venues": data
            },
            description="Venues fetched successfully"
        )

    def put(self, request, venue_id):
        venue = Venue.objects.filter(id=venue_id).first()
        if not venue:
            return CustomResponse().errorResponse(
                data={},
                description="Venue not found"
            )
        venue.name = request.data.get(
            "name",
            venue.name
        )
        venue.address = request.data.get(
            "address",
            venue.address
        )
        venue.latitude = request.data.get(
            "latitude",
            venue.latitude
        )
        venue.longitude = request.data.get(
            "longitude",
            venue.longitude
        )
        venue.cover_image = request.data.get(
            "cover_image",
            venue.cover_image
        )
        venue.opening_time = request.data.get(
            "opening_time",
            venue.opening_time
        )
        venue.closing_time = request.data.get(
            "closing_time",
            venue.closing_time
        )
        venue.contact_number = request.data.get(
            "contact_number",
            venue.contact_number
        )
        venue.description = request.data.get(
            "description",
            venue.description
        )
        venue.save()
        return CustomResponse().successResponse(
            data={},
            description="Venue updated successfully"
        )

    def delete(self, request, venue_id):
        venue = Venue.objects.filter(id=venue_id).first()
        if not venue:
            return CustomResponse().errorResponse(
                data={},
                description="Venue not found"
            )
        venue.is_active = False
        venue.save()
        return CustomResponse().successResponse(
            data={},
            description="Venue deleted successfully"
        )


class AmenitiesApi(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = request.data.get("name")
        description = request.data.get("description")
        icon = request.data.get("icon")
        display_order = request.data.get("display_order", 0)
        if not name:
            return CustomResponse().errorResponse(
                data={},
                description="Amenity name is required"
            )
        amenity_exists = Amenity.objects.filter(
            name__iexact=name.strip(),
            is_active=True
        ).exists()
        if amenity_exists:
            return CustomResponse().errorResponse(
                data={},
                description="Amenity already exists"
            )
        amenity = Amenity.objects.create(
            name=name.strip(),
            description=description,
            icon=icon,
            display_order=display_order
        )
        return CustomResponse().successResponse(
            data={
                "id": str(amenity.id)
            },
            description="Amenity created successfully"
        )

    def get(self, request):
        search = request.GET.get("search")
        amenities = Amenity.objects.filter(
            is_active=True
        ).order_by(
            "display_order",
            "name"
        )
        if search:
            amenities = amenities.filter(
                name__icontains=search.strip()
            )
        data = []
        for amenity in amenities:
            data.append({
                "id": str(amenity.id),
                "name": amenity.name,
                "description": amenity.description,
                "icon": amenity.icon,
                "display_order": amenity.display_order
            })
        return CustomResponse().successResponse(
            data={
                "amenities": data
            },
            description="Amenities fetched successfully"
        )

    def put(self, request, amenity_id):
        try:
            amenity = Amenity.objects.get(
                id=amenity_id,
            )
        except Amenity.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Amenity not found"
            )
        name = request.data.get("name")
        if name:
            amenity_exists = Amenity.objects.filter(
                name__iexact=name.strip(),
                is_active=True
            ).exclude(
                id=amenity.id
            ).exists()
            if amenity_exists:
                return CustomResponse().errorResponse(
                    data={},
                    description="Amenity already exists"
                )
            amenity.name = name.strip()
        amenity.description = request.data.get(
            "description",
            amenity.description
        )
        amenity.is_active = request.data.get(
            "is_active",
            amenity.is_active
        )
        amenity.icon = request.data.get(
            "icon",
            amenity.icon
        )
        amenity.display_order = request.data.get(
            "display_order",
            amenity.display_order
        )
        amenity.save()
        return CustomResponse().successResponse(
            data={},
            description="Amenity updated successfully"
        )
    def delete(self, request, amenity_id):
        try:
            amenity = Amenity.objects.get(
                id=amenity_id,
                is_active=True
            )
        except Amenity.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Amenity not found"
            )
        amenity.is_active = False
        amenity.save(
            update_fields=["is_active"]
        )
        return CustomResponse().successResponse(
            data={},
            description="Amenity deleted successfully"
        )


class VenueAmenitiesApi(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        venue_id = request.data.get("venue_id")
        amenity_id = request.data.get("amenity_id")
        if not venue_id:
            return CustomResponse().errorResponse(
                data={},
                description="Venue is required"
            )
        if not amenity_id:
            return CustomResponse().errorResponse(
                data={},
                description="Amenity is required"
            )
        try:
            venue = Venue.objects.get(
                id=venue_id,
                is_active=True
            )
        except Venue.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Venue not found"
            )
        try:
            amenity = Amenity.objects.get(
                id=amenity_id,
                is_active=True
            )
        except Amenity.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Amenity not found"
            )
        mapping = VenueAmenity.objects.filter(
            venue=venue,
            amenity=amenity
        ).first()
        if mapping:
            return CustomResponse().errorResponse(
                data={
                    "id": str(mapping.id)
                },
                description="Venue amenity already exist"
            )
        mapping = VenueAmenity.objects.create(
            venue=venue,
            amenity=amenity
        )
        return CustomResponse().successResponse(
            data={
                "id": str(mapping.id)
            },
            description="Venue amenity mapped successfully"
        )
    def get(self, request):

        venue_id = request.GET.get("venue_id")

        mappings = VenueAmenity.objects.filter(
            is_active=True
        ).select_related(
            "venue",
            "amenity"
        )

        if venue_id:
            mappings = mappings.filter(
                venue_id=venue_id
            )

        data = []

        for mapping in mappings:

            data.append({
                "id": str(mapping.id),
                "venue": {
                    "id": str(mapping.venue.id),
                    "name": mapping.venue.name
                },
                "amenity": {
                    "id": str(mapping.amenity.id),
                    "name": mapping.amenity.name,
                    "icon": mapping.amenity.icon
                }
            })

        return CustomResponse().successResponse(
            data={
                "venue_amenities": data
            },
            description="Venue amenities fetched successfully"
        )

    def delete(self, request, venue_amenity_id):
        try:
            mapping = VenueAmenity.objects.get(
                id=venue_amenity_id
            )
        except VenueAmenity.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Venue amenity not found"
            )
        mapping.delete()
        return CustomResponse().successResponse(
            data={},
            description="Venue amenity removed successfully"
        )