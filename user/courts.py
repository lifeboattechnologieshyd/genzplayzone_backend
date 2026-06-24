from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import Court
from shared.utils import CustomResponse


class CourtsApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        sport_id = request.GET.get("sport_id")
        venue_id = request.GET.get("venue_id")

        courts = Court.objects.filter(
            is_active=True,
            venue__is_active=True
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
            for court_sport in court.court_sports.filter(
                is_active=True
            ):
                sports.append({
                    "id": str(court_sport.sport.id),
                    "name": court_sport.sport.name
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
                "slot_duration_minutes": court.slot_duration_minutes,
                "max_players": court.max_players
            })
        return CustomResponse().successResponse(
            data={
                "courts": data
            },
            description="Courts fetched successfully"
        )