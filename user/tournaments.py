from rest_framework.views import APIView

from db.models import Tournament, TournamentParticipant
from shared.utils import CustomResponse


class TournamentListAPI(APIView):

    def get(self, request):

        try:
            sport_id = request.GET.get("sport_id")
            status_filter = request.GET.get("status")

            tournaments = Tournament.objects.select_related(
                "sport",
                "venue"
            ).filter(
                status__in=[
                    Tournament.STATUS_OPEN,
                    Tournament.STATUS_FULL,
                    Tournament.STATUS_ONGOING,
                    Tournament.STATUS_COMPLETED
                ]
            ).order_by("-tournament_date")

            # Sport filter
            if sport_id:
                tournaments = tournaments.filter(
                    sport_id=sport_id
                )

            # Optional status filter
            if status_filter:
                tournaments = tournaments.filter(
                    status=status_filter
                )

            data = []

            for tournament in tournaments:
                # Check current user's registration
                is_joined = tournament.participants.filter(
                    user=request.user,
                    payment_status=(
                        TournamentParticipant.PAYMENT_SUCCESS
                    )
                ).exists()

                registered_count = (
                    tournament.registered_participants_count
                )

                remaining_slots = max(
                    tournament.max_participants - registered_count,
                    0
                )

                data.append({
                    "id": str(tournament.id),

                    "name": tournament.name,

                    "sport": {
                        "id": str(tournament.sport.id),
                        "name": tournament.sport.name,
                        "icon": tournament.sport.icon,
                        "image": tournament.sport.image
                    },

                    "venue": {
                        "id": str(tournament.venue.id),
                        "name": tournament.venue.name,
                        "address": tournament.venue.address
                    },
                    "banner": tournament.banner,
                    "tournament_date": (
                        tournament.tournament_date
                    ),
                    "registration_deadline": (
                        tournament.registration_deadline
                    ),
                    "registration_fee": str(
                        tournament.registration_fee
                    ),
                    "prize_pool": str(
                        tournament.prize_pool
                    ),
                    "max_participants": (
                        tournament.max_participants
                    ),
                    "registered_participants": (
                        registered_count
                    ),
                    "remaining_slots": (
                        remaining_slots
                    ),
                    "status": tournament.status,
                    "is_joined": tournament.is_joined
                })

            return CustomResponse.successResponse(
                data=data,
                total=len(data),
                description="Tournaments fetched successfully"
            )

        except Exception as e:

            return CustomResponse.errorResponse(
                description=str(e)
            )