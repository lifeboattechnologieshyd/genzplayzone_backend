from django.urls import path
from .views import SendOtp, VerifyOTP, FileUploadView

urlpatterns = [
    path("send-otp", SendOtp.as_view()),
    path("verify-otp", VerifyOTP.as_view()),

    # need to add apis here.
    path("file/upload",FileUploadView.as_view()),

]