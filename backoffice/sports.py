from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import Sport
from shared.utils import CustomResponse


class SportsApi(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        name = request.data.get("name")
        description = request.data.get("description")
        icon = request.data.get("icon")
        display_order = request.data.get(
            "display_order",
            0
        )
        if not name:
            return CustomResponse().errorResponse(data={}, description="Sport name is required")

        sport_exists = Sport.objects.filter(
            name__iexact=name.strip()
        ).exists()
        if sport_exists:
            return CustomResponse().errorResponse(data={}, description="Sport already exists")

        sport = Sport.objects.create(
            name=name.strip(),
            description=description,
            icon=icon,
            display_order=display_order,
            created_by=request.user
        )
        return CustomResponse().successResponse(data={
                "id": str(sport.id),
                "name": sport.name,
                "description": sport.description,
                "icon": sport.icon,
                "display_order": sport.display_order
            }, description="Sport created successfully")

    def get(self, request):
        search = request.GET.get("search")
        queryset = Sport.objects.filter(
            is_active=True
        ).order_by(
            "display_order",
            "name"
        )

        if search:
            queryset = queryset.filter(
                name__icontains=search.strip()
            )
        sports = []
        for sport in queryset:
            sports.append({
                "id": str(sport.id),
                "name": sport.name,
                "description": sport.description,
                "icon": sport.icon,
                "display_order": sport.display_order
            })
        return CustomResponse().successResponse(
            data={
                "sports": sports
            },
            description="Sports fetched successfully"
        )

    def put(self, request, sport_id):
        try:
            sport = Sport.objects.get(
                id=sport_id,
            )
        except Sport.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Sport not found"
            )
        name = request.data.get("name")
        if name:
            sport_exists = Sport.objects.filter(
                name__iexact=name.strip(),
                is_active=True
            ).exclude(
                id=sport.id
            ).exists()
            if sport_exists:
                return CustomResponse().errorResponse(
                    data={},
                    description="Sport already exists"
                )
            sport.name = name.strip()
        sport.description = request.data.get(
            "description",
            sport.description
        )
        sport.icon = request.data.get(
            "icon",
            sport.icon
        )
        sport.display_order = request.data.get(
            "display_order",
            sport.display_order
        )
        sport.save()
        return CustomResponse().successResponse(
            data={},
            description="Sport updated successfully"
        )

    def delete(self, request, sport_id):
        try:
            sport = Sport.objects.get(
                id=sport_id,
            )
        except Sport.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Sport not found"
            )
        sport.is_active = False
        sport.save(
            update_fields=["is_active"]
        )
        return CustomResponse().successResponse(
            data={},
            description="Sport deleted successfully"
        )