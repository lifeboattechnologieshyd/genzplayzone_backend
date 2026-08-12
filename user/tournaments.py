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
                    "is_joined": is_joined
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


class MyTournamentListAPI(APIView):

    def get(self, request):

        try:
            status_filter = request.GET.get("status")
            participants = TournamentParticipant.objects.filter(
                user=request.user
            ).select_related(
                "tournament",
                "tournament__sport",
                "tournament__venue"
            ).order_by(
                "-registered_at"
            )

            if status_filter:
                participants = participants.filter(
                    tournament__status=status_filter
                )

            data = []

            for participant in participants:
                tournament = participant.tournament
                result = getattr(
                    participant,
                    "result",
                    None
                )

                item = {
                    "id": str(tournament.id),

                    "name": tournament.name,

                    "sport": {
                        "id": str(tournament.sport.id),
                        "name": tournament.sport.name
                    },

                    "venue": {
                        "id": str(tournament.venue.id),
                        "name": tournament.venue.name
                    },

                    "banner": tournament.banner,

                    "tournament_date": (
                        tournament.tournament_date
                    ),

                    "registration_fee": str(
                        tournament.registration_fee
                    ),

                    "status": tournament.status,

                    "payment_status": (
                        participant.payment_status
                    ),

                    "registered_at": (
                        participant.registered_at
                    )
                }

                # Result available only after completion
                if result:
                    d = {
                        "rank": result.rank,
                        "points": result.points,
                        "prize_amount": str(result.prize_amount)
                    }
                    item["result"] = d
                else:
                    item["result"] = None
                data.append(item)
            return CustomResponse.successResponse(
                data=data,
                total=len(data),
                description="My tournaments fetched successfully"
            )

        except Exception as e:
            return CustomResponse.errorResponse(
                description=str(e)
            )


from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView

class TournamentJoinAPI(APIView):

    @transaction.atomic
    def post(self, request, tournament_id):

        try:
            tournament = (
                Tournament.objects
                .select_for_update()
                .get(id=tournament_id)
            )
            # --------------------------------
            # Check tournament status
            # --------------------------------
            if tournament.status != Tournament.STATUS_OPEN:
                return CustomResponse.errorResponse(
                    description="Tournament is not open for registration"
                )
            # --------------------------------
            # Check registration deadline
            # --------------------------------
            if timezone.now() >= tournament.registration_deadline:
                return CustomResponse.errorResponse(
                    description="Tournament registration is closed"
                )
            # --------------------------------
            # Check existing registration
            # --------------------------------
            participant = (
                TournamentParticipant.objects
                .filter(
                    tournament=tournament,
                    user=request.user
                )
                .first()
            )
            if participant:
                if participant.payment_status == (
                    TournamentParticipant.PAYMENT_SUCCESS
                ):
                    return CustomResponse.errorResponse(
                        description="You have already joined this tournament"
                    )
                if participant.payment_status == (
                    TournamentParticipant.PAYMENT_PENDING
                ):
                    return CustomResponse.errorResponse(
                        description="You already have a pending payment"
                    )
            else:

                registered_count = (
                    TournamentParticipant.objects
                    .filter(
                        tournament=tournament,
                        payment_status=(
                            TournamentParticipant.PAYMENT_SUCCESS
                        )
                    )
                    .count()
                )
                if registered_count >= tournament.max_participants:
                    tournament.status = Tournament.STATUS_FULL
                    tournament.save()
                    return CustomResponse.errorResponse(
                        description="Tournament is full"
                    )
                participant = TournamentParticipant.objects.create(
                    tournament=tournament,
                    user=request.user,
                    payment_status=(
                        TournamentParticipant.PAYMENT_PENDING
                    )
                )

            # --------------------------------
            # FREE TOURNAMENT
            # --------------------------------

            if tournament.registration_fee <= 0:
                participant.payment_status = (
                    TournamentParticipant.PAYMENT_SUCCESS
                )
                participant.payment_reference = (
                    f"FREE-{participant.id}"
                )
                participant.save()
                return CustomResponse.successResponse(
                    data={
                        "participant_id": str(participant.id),
                        "tournament_id": str(tournament.id),
                        "payment_required": False
                    },
                    description="Successfully joined tournament"
                )
            return CustomResponse.successResponse(
                data={
                    "participant_id": str(participant.id),
                    "tournament_id": str(tournament.id),
                    "payment_required": True,
                    "amount": str(
                        tournament.registration_fee
                    ),
                    "payment_status": participant.payment_status
                },
                description="Tournament registration initiated"
            )

        except Tournament.DoesNotExist:
            return CustomResponse.errorResponse(
                description="Tournament not found"
            )

        except Exception as e:
            return CustomResponse.errorResponse(
                description=str(e)
            )