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