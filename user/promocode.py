from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models.promocode import PromoCode
from shared.utils import CustomResponse, get_promo_data

class PromoCodeAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        promo_codes = PromoCode.objects.all().order_by("-created_at")
        is_active = request.GET.get("is_active")
        search = request.GET.get("search")
        if is_active in ["true", "false"]:
            promo_codes = promo_codes.filter(
                is_active=is_active == "true"
            )
        if search:
            promo_codes = promo_codes.filter(
                code__icontains=search.strip()
            )
        return CustomResponse().successResponse(
            data={
                "promo_codes": [
                    get_promo_data(promo_code)
                    for promo_code in promo_codes
                ]
            },
            description="Promo codes fetched successfully."
        )
