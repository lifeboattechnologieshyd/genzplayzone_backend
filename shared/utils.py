import random

from rest_framework.response import Response
from rest_framework import status

from db.models import CourtPricing


def getReferralCode():
    return f"GENZ{random.randint(10000, 99999)}"


class CustomResponse:

    @staticmethod
    def successResponse(
        data, errorCode=0, description="Request Successful", total=0, status=status.HTTP_200_OK, **kwargs
    ):
        return Response(
            {
                "success": True,
                "errorCode": errorCode,
                "description": description,
                "total": total,
                **kwargs,
                "data": data,
            },
            status=status,
        )

    @staticmethod
    def errorResponse(
        data=None,
        errorCode=0,
        description="Request Failed",
        total=0,
        status=status.HTTP_200_OK,
        **kwargs,
    ):
        if data is None:
            data = {}
        return Response(
            {
                "success": False,
                "errorCode": errorCode,
                "description": description,
                "total": total,
                "data": data,
                **kwargs,
            },
            status=status,
        )


from django.db.models import Min

def update_starting_price(court):
    lowest_price = CourtPricing.objects.filter(
        court=court,
        is_active=True
    ).aggregate(
        Min("price")
    )
    court.starting_price = lowest_price["price__min"] or 0
    court.save(update_fields=["starting_price"])