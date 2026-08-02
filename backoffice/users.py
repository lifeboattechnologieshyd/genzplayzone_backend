import random
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from db.models import UserMaster, OTPs
from shared.clients.sms import send_sms_to_mobile
from shared.utils import CustomResponse, getReferralCode


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

class BackofficeCreateUsersApi(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = request.data.get("name")
        phone = request.data.get("mobile")

        if not name:
            return CustomResponse().errorResponse(
                data={},
                description="name is required"
            )

        if not phone:
            return CustomResponse().errorResponse(
                data={},
                description="Phone number is required"
            )

        user = UserMaster.objects.filter(mobile=phone).first()
        if user:
            if user.mobile_verified:
                return CustomResponse().successResponse(
                    data={
                        "user_id": str(user.id),
                        "mobile_verified": True
                    },
                    description="User already exists"
                )
        otp = str(random.randint(1000, 9999))
        OTPs.objects.create(
            mobile_number=phone,
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=5),
            is_active=True
        )
        var = f"{otp}|"
        send_sms_to_mobile(var, phone, 12558)
        print(f"OTP for {phone} : {otp}")
        return CustomResponse().successResponse(
            data={
                "user_id": str(user.id),
                "mobile_verified": False
            },
            description="OTP sent successfully"
        )


class BackofficeVerifyUserApi(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        mobile = request.data.get("mobile")
        otp = request.data.get("otp")
        if not mobile:
            return CustomResponse().errorResponse(
                data={},
                description="mobile is required"
            )
        if not otp:
            return CustomResponse().errorResponse(
                data={},
                description="OTP is required"
            )
        otp_record = OTPs.objects.filter(
            mobile_number=mobile,
            otp=otp,
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()
        if not otp_record:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid or expired OTP"
            )
        otp_record.is_active = False
        otp_record.save()
        user = UserMaster.objects.filter(
            mobile=mobile
        ).first()
        if not user:
            user = UserMaster.objects.create_user(
                mobile=mobile,
                is_mobile_verified=True,
                referral_code=getReferralCode(),
                user_role = ["user"]
            )
        else:
            return CustomResponse().errorResponse(
                data={},
                description="Mobile Already Exists"
            )
        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at"])
        return CustomResponse().successResponse(
            data={
                "id": str(user.id),
                "name": user.full_name,
                "mobile": user.mobile,
                "email": user.email,
                "profile_image": user.profile_image,
                "roles": user.user_role,
                "created_at": user.created_at
            },
            description="Mobile verified successfully"
        )
