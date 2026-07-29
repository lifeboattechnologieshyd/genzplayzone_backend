from django.urls import path

from .booking import BookingsApi, CourtAvailabilityApi, PhonePeCallBack, PaymentResult, CheckInAPI, CancelBookingAPI
from .courts import CourtsApi, CourtPricingApi
from .promocode import PromoCodeAPI
from .sports import SportsApi
from .support import CreateSupportTicketAPIView, SupportTicketDetailAPIView, SendSupportMessageAPIView, \
    SubmitSupportTicketRatingAPIView
from .views import SendOtp, VerifyOTP, FileUploadView, BannersApi, ProfileApi

urlpatterns = [
    path("send-otp", SendOtp.as_view()),
    path("verify-otp", VerifyOTP.as_view()),

    path("profile", ProfileApi.as_view()),

    path("file/upload", FileUploadView.as_view()),
    path("sports",SportsApi.as_view()),
    path("banners",BannersApi.as_view()),
    path("courts",CourtsApi.as_view()),
    path("pricing",CourtAvailabilityApi.as_view()),
    path("promo-codes",PromoCodeAPI.as_view()),

    path("booking", BookingsApi.as_view()),
    path("phonepe/callback", PhonePeCallBack.as_view()),
    path("payment/result", PaymentResult.as_view()),
    path("booking/check-in", CheckInAPI.as_view()),
    path("booking/cancel", CancelBookingAPI.as_view()),

    path("support/tickets",CreateSupportTicketAPIView.as_view()),
    path("support/tickets/<uuid:ticket_id>/",SupportTicketDetailAPIView.as_view()),
    path("support/tickets/message", SendSupportMessageAPIView.as_view()),
    path("support/tickets/rate",SubmitSupportTicketRatingAPIView.as_view()),

]