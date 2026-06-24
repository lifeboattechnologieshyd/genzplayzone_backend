from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import Banner
from shared.utils import CustomResponse


class BannersApi(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        title = request.data.get("title")
        description = request.data.get("description")
        image = request.data.get("image")
        redirect_type = request.data.get("redirect_type")
        redirect_value = request.data.get("redirect_value")
        display_order = request.data.get("display_order", 0)

        if not image:
            return CustomResponse().errorResponse(
                data={},
                description="Banner image is required"
            )

        banner = Banner.objects.create(
            title=title,
            description=description,
            image=image,
            redirect_type=redirect_type,
            redirect_value=redirect_value,
            display_order=display_order
        )

        return CustomResponse().successResponse(
            data={
                "id": str(banner.id)
            },
            description="Banner created successfully"
        )

    def get(self, request):

        banners = Banner.objects.filter(
            is_active=True
        ).order_by(
            "display_order"
        )

        data = []

        for banner in banners:
            data.append({
                "id": str(banner.id),
                "title": banner.title,
                "description": banner.description,
                "image": banner.image,
                "redirect_type": banner.redirect_type,
                "redirect_value": banner.redirect_value,
                "display_order": banner.display_order
            })

        return CustomResponse().successResponse(
            data={
                "count": len(data),
                "banners": data
            },
            description="Banners fetched successfully"
        )

    def put(self, request, banner_id):

        try:
            banner = Banner.objects.get(
                id=banner_id,
                is_active=True
            )
        except Banner.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Banner not found"
            )
        banner.title = request.data.get(
            "title",
            banner.title
        )
        banner.description = request.data.get(
            "description",
            banner.description
        )
        banner.image = request.data.get(
            "image",
            banner.image
        )
        banner.redirect_type = request.data.get(
            "redirect_type",
            banner.redirect_type
        )
        banner.redirect_value = request.data.get(
            "redirect_value",
            banner.redirect_value
        )
        banner.display_order = request.data.get(
            "display_order",
            banner.display_order
        )
        banner.save()
        return CustomResponse().successResponse(
            data={},
            description="Banner updated successfully"
        )

    def delete(self, request, banner_id):

        try:
            banner = Banner.objects.get(
                id=banner_id,
                is_active=True
            )
        except Banner.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Banner not found"
            )
        banner.is_active = False
        banner.save(
            update_fields=["is_active"]
        )
        return CustomResponse().successResponse(
            data={},
            description="Banner deleted successfully"
        )