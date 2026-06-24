from django.urls import path

from .courts import CourtsApi
from .sports import SportsApi
from .views import SendOtp, VerifyOTP, FileUploadView, BannersApi

urlpatterns = [
    path("send-otp", SendOtp.as_view()),
    path("verify-otp", VerifyOTP.as_view()),
    path("file/upload", FileUploadView.as_view()),
    path("sports",SportsApi.as_view()),
    path("banners",BannersApi.as_view()),
    path("courts",CourtsApi.as_view()),


]