
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import Venue
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
        venue = Venue.objects.filter(id=venue_id)
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
        venue = Venue.objects.filter(id=venue_id)
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