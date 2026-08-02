from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from db.models import UserMaster
from shared.utils import CustomResponse


class BackofficeUsersApi(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):

        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 20))

        is_admin = request.GET.get("is_admin", False)
        search = request.GET.get("search")

        users = UserMaster.objects.all().order_by("-created_at")

        if is_admin:
            users = users.filter(user_role__contains=['admin'])


        if search:
            users = users.filter(
                mobile__icontains=search
            )
        total_count = users.count()
        start = (page - 1) * page_size
        end = start + page_size
        users = users[start:end]
        data = []
        for user in users:
            data.append({
                "id": str(user.id),
                "name": user.full_name,
                "mobile": user.mobile,
                "email": user.email,
                "profile_image": user.profile_image,
                "roles": user.user_role,
                "created_at": user.created_at
            })

        return CustomResponse().successResponse(
            data={
                "count": total_count,
                "page": page,
                "page_size": page_size,
                "results": data
            },
            description="Users fetched successfully"
        )