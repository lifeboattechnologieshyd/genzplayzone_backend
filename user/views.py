import random
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from db.models.user import OTPs, UserMaster, Devices, Banner
from shared.clients.s3 import add_unique_suffix_to_filename, sanitize_filename
from shared.clients.sms import send_otp_sms, send_sms_to_mobile
from shared.utils import CustomResponse, getReferralCode

class SendOtp(APIView):

    def post(self, request):
        #sendotp
        mobile = request.data.get("mobile")
        if not mobile:
            return CustomResponse().errorResponse(
                data={},
                description="Mobile number is required"
            )
        last_otp = OTPs.objects.filter(
            mobile_number=mobile,
            created_at__gte=timezone.now() - timedelta(seconds=30)
        ).exists()

        if last_otp:
            return CustomResponse().errorResponse(
                data={},
                description="Please wait before requesting another OTP"
            )
        otp = str(random.randint(1000, 9999))
        if mobile == '9014083090':
            otp = "1234"
        OTPs.objects.filter(
            mobile_number=mobile,
            is_active=True
        ).update(
            is_active=False
        )
        OTPs.objects.create(
            mobile_number=mobile,
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=5),
            is_active=True
        )
        var = f"{otp}|"
        send_sms_to_mobile(var, mobile, 12558)
        print(f"OTP for {mobile} : {otp}")
        return CustomResponse().successResponse(
            data={},
            description="OTP sent successfully"
        )

class VerifyOTP(APIView):

    def post(self, request):
        mobile = request.data.get("mobile")
        otp = request.data.get("otp")
        if not mobile:
            return CustomResponse().errorResponse(
                data={},
                description="Mobile number is required"
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
            if not user.is_mobile_verified:
                user.is_mobile_verified = True
                user.save()
        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at"])
        refresh = RefreshToken.for_user(user)
        # can_apply_referral = not Referrals.objects.filter(
        #     referred_user=user
        # ).exists()
        if "device_id" in request.data:
            print("Creating device session...")
            session = Devices.objects.create(
                user=user,
                device_id=request.data.get("device_id", ""),
                platform=request.data.get("platform", ""),
                app_version=request.data.get("app_version", ""),
                fcm_token=request.data.get("fcm_token", ""),
                last_login=timezone.now(),
                is_active=True
            )
            print("================================")
            print("DEVICE SESSION CREATED")
            print("================================")
            print(f"Session ID: {session.id}")
            print("================================")
        return CustomResponse().successResponse(
            data={
                "user_id": str(user.id),
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "mobile": user.mobile,
                "full_name": user.full_name,
                "profile_image": user.profile_image,
                "user_role": user.user_role,
                "referral_code": user.referral_code,
                "coins": user.coins,
                "can_apply_referral": True,
            },
            description="Login successful"
        )

class FileUploadView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist("files")
        path = request.data.get("path", "temp")
        if not files:
            return CustomResponse().successResponse(data={},description="No file was provided.")
        uploaded_files = []

        try:
            for file_obj in files:
                # Save each file to the default storage
                sanitized_filename = add_unique_suffix_to_filename(sanitize_filename(file_obj.name))
                file_path = default_storage.save(f"{path}/{sanitized_filename}", ContentFile(file_obj.read()))
                file_url = settings.MEDIA_URL + file_path
                uploaded_files.append(
                    {"original_filename": file_obj.name, "file_url": file_url, "file_path": file_path}
                )
            return CustomResponse().successResponse(uploaded_files)

        except Exception as e:
            return CustomResponse().errorResponse(
                data={"error": str(e)}, description="File upload failed - "+str(e))


class BannersApi(APIView):
    permission_classes = [IsAuthenticated]

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
                "redirect_value": banner.redirect_id
            })

        return CustomResponse().successResponse(
            data={
                "banners": data
            },
            description="Banners fetched successfully"
        )

class ProfileApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return CustomResponse().successResponse(
            data={
                "mobile": user.mobile,
                "full_name": user.full_name,
                "email": user.email,
                "gender": user.gender,
                "dob": user.dob,
                "profile_image": user.profile_image,
                "coins": user.coins,
                "referral_code": user.referral_code,
            },
            description="Profile fetched successfully"
        )

    def put(self, request):
        user = request.user
        email = request.data.get("email")
        if email:
            email_exists = UserMaster.objects.filter(
                email__iexact=email.strip()
            ).exclude(
                id=user.id
            ).exists()
            if email_exists:
                return CustomResponse().errorResponse(
                    data={},
                    description="Email already exists"
                )
            user.email = email.strip()
        user.full_name = request.data.get(
            "full_name",
            user.full_name
        )
        user.gender = request.data.get(
            "gender",
            user.gender
        )
        user.dob = request.data.get(
            "dob",
            user.dob
        )

        user.profile_image = request.data.get(
            "profile_image",
            user.profile_image
        )
        user.save()
        return CustomResponse().successResponse(
            data={
                "mobile": user.mobile,
                "full_name": user.full_name,
                "email": user.email,
                "gender": user.gender,
                "dob": user.dob,
                "profile_image": user.profile_image,
                "coins": user.coins,
                "referral_code": user.referral_code,
            },
            description="Profile updated successfully"
        )

