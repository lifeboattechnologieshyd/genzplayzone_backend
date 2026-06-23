from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from db.models import Sport
from shared.utils import CustomResponse


class SportsApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        sports = Sport.objects.filter(
            is_active=True
        ).order_by(
            "display_order",
            "name"
        )

        data = []

        for sport in sports:
            data.append({
                "id": str(sport.id),
                "name": sport.name,
                "icon": sport.icon
            })

        return CustomResponse().successResponse(
            data={
                "sports": data,
                "count": len(data)
            },
            description="Sports fetched successfully"
        )