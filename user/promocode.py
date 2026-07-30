from datetime import datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import Court
from db.models.promocode import PromoCode
from shared.utils import CustomResponse, get_promo_data, validate_booking_datetime, check_slot_availability, \
    calculate_booking_amount, get_promo_preview


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


class ApplyPromoCodeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        court_id = request.data.get("court_id")
        booking_date_value = request.data.get("booking_date")
        slots = request.data.get("slots", [])
        promo_code_value = request.data.get("promo_code")

        if not court_id:
            return CustomResponse().errorResponse(
                data={},
                description="Court is required."
            )

        if not booking_date_value:
            return CustomResponse().errorResponse(
                data={},
                description="Booking date is required."
            )

        if not slots:
            return CustomResponse().errorResponse(
                data={},
                description="Please select at least one slot."
            )

        if not promo_code_value:
            return CustomResponse().errorResponse(
                data={},
                description="Promo code is required."
            )

        try:
            booking_date = datetime.strptime(
                booking_date_value,
                "%Y-%m-%d"
            ).date()

            validate_booking_datetime(booking_date, slots)

            court = Court.objects.get(
                id=court_id,
                is_active=True,
                venue__is_active=True
            )
            check_slot_availability(
                court,
                booking_date,
                slots
            )

            subtotal_amount, slot_prices = calculate_booking_amount(
                court,
                booking_date,
                slots
            )

            promo_code, discount_amount = get_promo_preview(
                promo_code_value=promo_code_value,
                user=request.user,
                subtotal_amount=subtotal_amount
            )
            final_amount = subtotal_amount - discount_amount
            return CustomResponse().successResponse(
                data={
                    "promo_code": promo_code.code,
                    "subtotal_amount": str(subtotal_amount),
                    "discount_amount": str(discount_amount),
                    "total_amount": str(final_amount),
                },
                description=(
                    f"Promo code applied. You saved ₹{discount_amount}."
                )
            )
        except Court.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Court not found."
            )

        except Exception as exc:
            return CustomResponse().errorResponse(
                data={},
                description=str(exc)
            )