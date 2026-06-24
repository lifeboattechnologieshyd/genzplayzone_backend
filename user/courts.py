from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import Court, CourtMedia
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
            "court_sports__sport"
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
            for court_sport in court.court_sports.filter(is_active=True):
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
            data.append({
                "id": str(court.id),
                "name": court.name,
                "description": court.description,
                "cover_image": court.cover_image,
                "venue": {
                    "id": str(court.venue.id),
                    "name": court.venue.name
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


