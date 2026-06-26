from datetime import datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import Court, CourtMedia, CourtPricing
from shared.utils import CustomResponse


class CourtsApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        sport_id = request.GET.get("sport_id")
        venue_id = request.GET.get("venue_id")

        courts = Court.objects.filter(is_active=True,
            venue__is_active=True
        ).select_related(
            "venue"
        ).prefetch_related(
            "media",
            "court_sports__sport",
            "venue__amenities__amenity"
        )
        if venue_id:
            courts = courts.filter(
                venue_id=venue_id
            )
        if sport_id:
            courts = courts.filter(
                court_sports__sport_id=sport_id,
                court_sports__is_active=True
            )
        courts = courts.distinct().order_by(
            "display_order",
            "name"
        )
        data = []
        for court in courts:
            sports = []
            for court_sport in court.court_sports.all():
                sports.append({
                    "id": str(court_sport.sport.id),
                    "name": court_sport.sport.name
                })
            media = []
            for item in court.media.filter(is_active=True).order_by("display_order"):
                media.append({
                    "id": str(item.id),
                    "image": item.image,
                    "display_order": item.display_order
                })
            amenities = []

            for venue_amenity in court.venue.amenities.all():
                amenities.append({
                    "id": str(venue_amenity.amenity.id),
                    "name": venue_amenity.amenity.name,
                    "icon": venue_amenity.amenity.icon
                })
            data.append({
                "id": str(court.id),
                "name": court.name,
                "description": court.description,
                "cover_image": court.cover_image,
                "venue": {
                    "id": str(court.venue.id),
                    "name": court.venue.name,
                    "amenities": amenities
                },
                "sports": sports,
                "media": media,
                "slot_duration_minutes": court.slot_duration_minutes,
                "max_players": court.max_players,
                "starting_price": court.starting_price,
                "avg_rating": court.avg_rating,
                "reviews": court.reviews_count,
            })
        return CustomResponse().successResponse(
            data={
                "courts": data
            },
            description="Courts fetched successfully"
        )


class CourtPricingApi(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        court_id = request.GET.get("court_id")
        booking_date = request.GET.get("date")
        if not court_id:
            return CustomResponse().errorResponse(
                data={},
                description="Court is required"
            )

        if not booking_date:
            return CustomResponse().errorResponse(
                data={},
                description="Booking date is required"
            )
        try:
            court = Court.objects.get(
                id=court_id,
                is_active=True
            )
        except Court.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Court not found"
            )

        try:
            booking_date = datetime.strptime(
                booking_date,
                "%Y-%m-%d"
            ).date()
        except Exception:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid date format. Use YYYY-MM-DD"
            )
        day = booking_date.strftime("%A").upper()
        pricing = CourtPricing.objects.filter(
            court=court,
            day=day,
            is_active=True
        ).order_by(
            "start_time"
        )
        data = []
        for item in pricing:
            data.append({
                "id": str(item.id),
                "start_time": item.start_time,
                "end_time": item.end_time,
                "price": item.price
            })
        return CustomResponse().successResponse(
            data={
                "court": {
                    "id": str(court.id),
                    "name": court.name
                },
                "date": booking_date,
                "day": day,
                "pricing": data
            },
            description="Pricing fetched successfully"
        )
