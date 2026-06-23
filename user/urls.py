from django.urls import path

from .sports import SportsApi
from .views import SendOtp, VerifyOTP, FileUploadView

urlpatterns = [
    path("send-otp", SendOtp.as_view()),
    path("verify-otp", VerifyOTP.as_view()),
    path("file/upload", FileUploadView.as_view()),

    path("sports",SportsApi.as_view())

]