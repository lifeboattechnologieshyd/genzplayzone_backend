from logging import exception

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import Venue, Court, Sport, CourtSport, CourtMedia, CourtPricing
from shared.utils import CustomResponse, update_starting_price


class CourtsApi(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, court_id):
        try:
            return Court.objects.get(
                id=court_id,
            )
        except Court.DoesNotExist:
            return None

    def post(self, request):
        venue_id = request.data.get("venue_id")
        name = request.data.get("name")
        description = request.data.get("description")
        cover_image = request.data.get("cover_image")
        starting_price = request.data.get("starting_price", 800)
        slot_duration_minutes = request.data.get(
            "slot_duration_minutes",
            60
        )
        max_players = request.data.get(
            "max_players",
            0
        )
        display_order = request.data.get(
            "display_order",
            0
        )
        sport_ids = request.data.get(
            "sport_ids",
            []
        )
        if not venue_id:
            return CustomResponse().errorResponse(
                data={},
                description="Venue is required"
            )
        if not name:
            return CustomResponse().errorResponse(
                data={},
                description="Court name is required"
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
        court = Court.objects.create(
            venue=venue,
            name=name,
            description=description,
            cover_image=cover_image,
            slot_duration_minutes=slot_duration_minutes,
            max_players=max_players,
            display_order=display_order,
            starting_price=starting_price,
        )
        for sport_id in sport_ids:
            try:
                sport = Sport.objects.get(
                    id=sport_id,
                    is_active=True
                )

                CourtSport.objects.create(
                    court=court,
                    sport=sport
                )
            except exception as error:
                return CustomResponse().errorResponse(
                    data={},
                    description=f"{error}"
                )
        return CustomResponse().successResponse(
            data={"id": str(court.id)},
            description="Court created successfully"
        )

    def get(self, request):
        venue_id = request.GET.get("venue_id")
        sport_id = request.GET.get("sport_id")
        courts = Court.objects.filter(
            is_active=True
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
        data = []
        for court in courts.distinct():
            sports = []
            for cs in court.court_sports.filter(
                is_active=True
            ):
                sports.append({
                    "id": str(cs.sport.id),
                    "name": cs.sport.name
                })
            data.append({
                "id": str(court.id),
                "name": court.name,
                "venue_id": str(court.venue.id),
                "venue_name": court.venue.name,
                "cover_image": court.cover_image,
                "slot_duration_minutes": court.slot_duration_minutes,
                "max_players": court.max_players,
                "sports": sports,
                "starting_price":court.starting_price,
            })
        return CustomResponse().successResponse(
            data={
                "courts": data
            },
            description="Courts fetched successfully"
        )

    def put(self, request, court_id):
        court = self.get_object(court_id)
        if not court:
            return CustomResponse().errorResponse(
                data={},
                description="Court not found"
            )
        court.name = request.data.get(
            "name",
            court.name
        )
        court.description = request.data.get(
            "description",
            court.description
        )
        court.starting_price = request.data.get(
            "starting_price",
            court.starting_price
        )
        court.cover_image = request.data.get(
            "cover_image",
            court.cover_image
        )
        court.slot_duration_minutes = request.data.get(
            "slot_duration_minutes",
            court.slot_duration_minutes
        )
        court.max_players = request.data.get(
            "max_players",
            court.max_players
        )
        court.display_order = request.data.get(
            "display_order",
            court.display_order
        )
        court.is_active = request.data.get(
            "is_active",
            court.is_active
        )
        court.save()
        sport_ids = request.data.get(
            "sport_ids"
        )
        if sport_ids is not None:
            CourtSport.objects.filter(
                court=court
            ).delete()
            for sport_id in sport_ids:
                try:
                    sport = Sport.objects.get(
                        id=sport_id,
                        is_active=True
                    )
                    CourtSport.objects.create(
                        court=court,
                        sport=sport
                    )
                except Sport.DoesNotExist:
                    continue
        return CustomResponse().successResponse(
            data={},
            description="Court updated successfully"
        )

    def delete(self, request, court_id):
        court = self.get_object(court_id)
        if not court:
            return CustomResponse().errorResponse(
                data={},
                description="Court not found"
            )
        court.is_active = False
        court.save()
        return CustomResponse().successResponse(
            data={},
            description="Court deleted successfully"
        )


class CourtMediaApi(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        court_id = request.data.get("court_id")
        image = request.data.get("image")
        display_order = request.data.get(
            "display_order",
            0
        )
        if not court_id:
            return CustomResponse().errorResponse(
                data={},
                description="Court is required"
            )
        if not image:
            return CustomResponse().errorResponse(
                data={},
                description="Image is required"
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
        media = CourtMedia.objects.create(
            court=court,
            image=image,
            display_order=display_order
        )
        return CustomResponse().successResponse(
            data={
                "id": str(media.id)
            },
            description="Court media created successfully"
        )

    def get(self, request):
        court_id = request.GET.get("court_id")
        media_queryset = CourtMedia.objects.filter(
            is_active=True
        )
        if court_id:
            media_queryset = media_queryset.filter(
                court_id=court_id
            )
        data = []
        for media in media_queryset.order_by(
            "display_order"
        ):
            data.append({
                "id": str(media.id),
                "court_id": str(media.court.id),
                "image": media.image,
                "display_order": media.display_order
            })
        return CustomResponse().successResponse(
            data={
                "media": data
            },
            description="Court media fetched successfully"
        )

    def put(self, request, media_id):
        try:
            media = CourtMedia.objects.get(
                id=media_id,
                is_active=True
            )
        except CourtMedia.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Court media not found"
            )
        media.image = request.data.get(
            "image",
            media.image
        )
        media.display_order = request.data.get(
            "display_order",
            media.display_order
        )
        media.save()
        return CustomResponse().successResponse(
            data={},
            description="Court media updated successfully"
        )

    def delete(self, request, media_id):
        try:
            media = CourtMedia.objects.get(
                id=media_id,
                is_active=True
            )
        except CourtMedia.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Court media not found"
            )
        media.is_active = False
        media.save(
            update_fields=["is_active"]
        )
        return CustomResponse().successResponse(
            data={},
            description="Court media deleted successfully"
        )


class CourtPricingsApi(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        court_id = request.data.get("court_id")
        day = request.data.get("day")
        start_time = request.data.get("start_time")
        end_time = request.data.get("end_time")
        price = request.data.get("price")
        if not court_id:
            return CustomResponse().errorResponse(
                data={},
                description="Court is required"
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
        if start_time >= end_time:
            return CustomResponse().errorResponse(
                data={},
                description="Start time should be less than end time"
            )
        overlap = CourtPricing.objects.filter(
            court=court,
            day=day,
            is_active=True,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()
        if overlap:
            return CustomResponse().errorResponse(
                data={},
                description="Pricing overlaps with existing pricing"
            )
        pricing = CourtPricing.objects.create(
            court=court,
            day=day,
            start_time=start_time,
            end_time=end_time,
            price=price
        )
        update_starting_price(court)
        return CustomResponse().successResponse(
            data={
                "id": str(pricing.id)
            },
            description="Pricing created successfully"
        )
    def get(self, request):
        court_id = request.GET.get("court_id")
        day = request.GET.get("day")
        pricings = CourtPricing.objects.filter(
            is_active=True
        ).select_related(
            "court"
        )
        if court_id:
            pricings = pricings.filter(
                court_id=court_id
            )
        if day:
            pricings = pricings.filter(
                day=day
            )
        data = []
        for pricing in pricings.order_by(
            "court__name",
            "day",
            "start_time"
        ):
            data.append({
                "id": str(pricing.id),
                "court": {
                    "id": str(pricing.court.id),
                    "name": pricing.court.name
                },
                "day": pricing.day,
                "start_time": pricing.start_time,
                "end_time": pricing.end_time,
                "price": pricing.price,
                "is_active": pricing.is_active
            })
        return CustomResponse().successResponse(
            data={
                "pricing": data
            },
            description="Pricing fetched successfully"
        )

    def put(self, request, pricing_id):
        try:
            pricing = CourtPricing.objects.get(
                id=pricing_id
            )
        except CourtPricing.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Pricing not found"
            )
        day = request.data.get(
            "day",
            pricing.day
        )
        start_time = request.data.get(
            "start_time",
            pricing.start_time
        )
        end_time = request.data.get(
            "end_time",
            pricing.end_time
        )
        if start_time >= end_time:
            return CustomResponse().errorResponse(
                data={},
                description="Start time should be less than end time"
            )
        overlap = CourtPricing.objects.filter(
            court=pricing.court,
            day=day,
            is_active=True,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(
            id=pricing.id
        ).exists()
        if overlap:
            return CustomResponse().errorResponse(
                data={},
                description="Pricing overlaps with existing pricing"
            )
        pricing.day = day
        pricing.start_time = start_time
        pricing.end_time = end_time
        pricing.price = request.data.get(
            "price",
            pricing.price
        )
        pricing.is_active = request.data.get(
            "is_active",
            pricing.is_active
        )
        pricing.save()
        update_starting_price(
            pricing.court
        )
        return CustomResponse().successResponse(
            data={},
            description="Pricing updated successfully"
        )

    def delete(self, request, pricing_id):
        try:
            pricing = CourtPricing.objects.get(
                id=pricing_id
            )
        except CourtPricing.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Pricing not found"
            )
        pricing.delete()
        return CustomResponse().successResponse(
            data={},
            description="Pricing deleted successfully"
        )