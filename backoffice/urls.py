from django.urls import path

from backoffice.sports import SportsApi
from backoffice.support import AdminSupportTicketsAPIView, AdminSupportTicketDetailAPIView, \
    AdminReplySupportTicketAPIView, AdminUpdateSupportTicketStatusAPIView
from backoffice.user import MobileSendOTPAdminView, MobileVerifyOTPAdminView

urlpatterns = [
    path("support/tickets", AdminSupportTicketsAPIView.as_view()),
    path("support/ticket-details", AdminSupportTicketDetailAPIView.as_view()),
    path("support/reply", AdminReplySupportTicketAPIView.as_view()),
    path("support/ticket/update", AdminUpdateSupportTicketStatusAPIView.as_view()),

    path("send-otp", MobileSendOTPAdminView.as_view()),
    path("verify-otp", MobileVerifyOTPAdminView.as_view()),

    path("sports", SportsApi.as_view()),
]