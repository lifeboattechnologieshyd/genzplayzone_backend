from rest_framework.views import APIView

from db.models.promocode import PromoCode
from shared.utils import CustomResponse, parse_decimal, parse_promo_datetime, get_promo_data


class PromocodeApi(APIView):

    def post(self, request):
        if request.user.user_role != "admin":
            return CustomResponse().errorResponse(
                data={},
                description="You don't have permission to access this."
            )
        try:
            code = request.data.get("code", "").strip().upper()
            if not code:
                return CustomResponse().errorResponse(
                    data={},
                    description="Promo code is required."
                )
            if PromoCode.objects.filter(code=code).exists():
                return CustomResponse().errorResponse(
                    data={},
                    description="This promo code already exists."
                )
            discount_amount = parse_decimal(
                request.data.get("discount_amount"),
                "Discount amount"
            )

            minimum_booking_amount = parse_decimal(
                request.data.get("minimum_booking_amount", 0),
                "Minimum booking amount",
                allow_zero=True
            )

            valid_from = parse_promo_datetime(
                request.data.get("valid_from"),
                "valid from date"
            )

            valid_until = parse_promo_datetime(
                request.data.get("valid_until"),
                "valid until date"
            )

            if valid_until <= valid_from:
                return CustomResponse().errorResponse(
                    data={},
                    description="Valid until date must be after valid from date."
                )

            total_usage_limit = request.data.get("total_usage_limit")
            per_user_usage_limit = request.data.get("per_user_usage_limit")
            if total_usage_limit not in [None, ""]:
                total_usage_limit = int(total_usage_limit)
                if total_usage_limit <= 0:
                    return CustomResponse().errorResponse(
                        data={},
                        description="Total usage limit must be greater than zero."
                    )
            else:
                total_usage_limit = None
            if per_user_usage_limit not in [None, ""]:
                per_user_usage_limit = int(per_user_usage_limit)

                if per_user_usage_limit <= 0:
                    return CustomResponse().errorResponse(
                        data={},
                        description="Per-user usage limit must be greater than zero."
                    )
            else:
                per_user_usage_limit = None
            promo_code = PromoCode.objects.create(
                code=code,
                discount_amount=discount_amount,
                minimum_booking_amount=minimum_booking_amount,
                valid_from=valid_from,
                valid_until=valid_until,
                total_usage_limit=total_usage_limit,
                per_user_usage_limit=per_user_usage_limit,
                is_active=request.data.get("is_active", True),
            )
            return CustomResponse().successResponse(
                data={
                    "promo_code": get_promo_data(promo_code)
                },
                description="Promo code created successfully."
            )
        except Exception as exc:
            return CustomResponse().errorResponse(
                data={},
                description=str(exc)
            )

    def get(self, request):
        if request.user.user_role != "admin":
            return CustomResponse().errorResponse(
                data={},
                description="You don't have permission to access this."
            )
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