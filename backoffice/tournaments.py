import json
from datetime import datetime

from django.utils import timezone
from django.views import View

from db.models import Sport, Venue, Tournament
from shared.utils import CustomResponse


class TournamentCrudAPI(View):

    def post(self, request):
        try:
            data = json.loads(request.body)

            name = data.get("name")
            sport_id = data.get("sport_id")
            venue_id = data.get("venue_id")
            tournament_date = data.get("tournament_date")
            registration_deadline = data.get("registration_deadline")
            registration_fee = data.get("registration_fee", 0)
            max_participants = data.get("max_participants")
            prize_pool = data.get("prize_pool", 0)
            description = data.get("description")
            rules = data.get("rules")
            banner = data.get("banner")

            # -------------------------
            # Required validation
            # -------------------------

            if not name:
                return CustomResponse.errorResponse(
                    description="Tournament name is required"
                )

            if not sport_id:
                return CustomResponse.errorResponse(
                    description="Sport is required"
                )

            if not venue_id:
                return CustomResponse.errorResponse(
                    description="Venue is required"
                )

            if not tournament_date:
                return CustomResponse.errorResponse(
                    description="Tournament date is required"
                )


            if not registration_deadline:
                return CustomResponse.errorResponse(
                    description="Registration deadline is required"
                )


            if not max_participants:
                return CustomResponse.errorResponse(
                    description="Maximum participants are required"
                )


            # -------------------------
            # Sport
            # -------------------------

            try:
                sport = Sport.objects.get(
                    id=sport_id,
                    is_active=True
                )
            except Sport.DoesNotExist:
                return CustomResponse.errorResponse(
                    description="Invalid or inactive sport"
                )


            # -------------------------
            # Venue
            # -------------------------

            try:
                venue = Venue.objects.get(
                    id=venue_id,
                    is_active=True
                )
            except Venue.DoesNotExist:
                return CustomResponse.errorResponse(
                    description="Invalid or inactive venue"
                )

            # -------------------------
            # Date validation
            # -------------------------

            try:
                tournament_date_obj = datetime.strptime(
                    tournament_date,
                    "%Y-%m-%d"
                ).date()
            except ValueError:
                return CustomResponse.errorResponse(
                    description="Invalid tournament date. Use YYYY-MM-DD"
                )
            try:
                deadline_obj = datetime.strptime(
                    registration_deadline,
                    "%Y-%m-%d %H:%M:%S"
                )

                deadline_obj = timezone.make_aware(
                    deadline_obj
                )

            except ValueError:
                return CustomResponse.errorResponse(
                    description="Invalid registration deadline. Use YYYY-MM-DD HH:MM:SS"
                )

            if deadline_obj.date() > tournament_date_obj:
                return CustomResponse.errorResponse(
                    description="Registration deadline cannot be after tournament date"
                )

            # -------------------------
            # Numeric validation
            # -------------------------

            try:
                registration_fee = float(
                    registration_fee
                )

                prize_pool = float(
                    prize_pool
                )

                max_participants = int(
                    max_participants
                )

                if registration_fee < 0:
                    raise ValueError

                if prize_pool < 0:
                    raise ValueError

                if max_participants <= 0:
                    raise ValueError

            except (ValueError, TypeError):
                return CustomResponse.errorResponse(
                    description="Invalid fee, prize pool or participant count"
                )

            # -------------------------
            # Create tournament
            # -------------------------
            tournament = Tournament.objects.create(
                name=name.strip(),
                sport=sport,
                venue=venue,
                banner=banner,
                description=description,
                tournament_date=tournament_date_obj,
                registration_deadline=deadline_obj,
                registration_fee=registration_fee,
                max_participants=max_participants,
                prize_pool=prize_pool,
                rules=rules,
                status=Tournament.STATUS_DRAFT
            )
            return CustomResponse.successResponse(data={
                    "id": str(tournament.id),
                    "name": tournament.name,
                    "sport": tournament.sport.name,
                    "venue": tournament.venue.name,
                    "status": tournament.status
                })

        except json.JSONDecodeError:
            return CustomResponse.errorResponse(description="Invalid Json")

        except Exception as e:
            return CustomResponse.errorResponse(description=str(e))

    def get(self, request):

        try:
            status = request.GET.get("status")
            sport_id = request.GET.get("sport_id")
            tournaments = Tournament.objects.select_related(
                "sport",
                "venue"
            ).all().order_by("-created_at")

            if status:
                tournaments = tournaments.filter(
                    status=status
                )

            if sport_id:
                tournaments = tournaments.filter(
                    sport_id=sport_id
                )

            result = []

            for tournament in tournaments:
                registered_count = (
                    tournament.registered_participants_count
                )

                result.append({
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

                    "tournament_date": tournament.tournament_date,

                    "registration_deadline":
                        tournament.registration_deadline,

                    "registration_fee":
                        str(tournament.registration_fee),

                    "max_participants":
                        tournament.max_participants,

                    "registered_participants":
                        registered_count,

                    "remaining_slots":
                        max(
                            tournament.max_participants -
                            registered_count,
                            0
                        ),

                    "prize_pool":
                        str(tournament.prize_pool),

                    "status":
                        tournament.status,

                    "created_at":
                        tournament.created_at
                })

            return CustomResponse.successResponse(data=result)
        except Exception as e:
            return CustomResponse.errorResponse(description=str(e))

class TournamentDeleteAPI(View):

    def delete(self, request, tournament_id):
        try:
            tournament = Tournament.objects.get(
                id=tournament_id
            )
            if tournament.status == Tournament.STATUS_COMPLETED:
                return CustomResponse.errorResponse(
                    description="Completed tournament cannot be deleted/cancelled"
                )
            tournament.status = Tournament.STATUS_CANCELLED
            tournament.save()
            #todo: refund to be added.
            return CustomResponse.successResponse(data={}, description="Tournament cancelled successfully")

        except Tournament.DoesNotExist:
            return CustomResponse.errorResponse(
                description="Tournament not found"
            )
        except Exception as e:
            return CustomResponse.errorResponse(
                description=str(e)
            )