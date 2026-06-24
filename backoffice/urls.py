from django.urls import path

from backoffice.banners import BannersApi
from backoffice.courts import CourtsApi, CourtMediaApi
from backoffice.sports import SportsApi
from backoffice.support import AdminSupportTicketsAPIView, AdminSupportTicketDetailAPIView, \
    AdminReplySupportTicketAPIView, AdminUpdateSupportTicketStatusAPIView
from backoffice.user import MobileSendOTPAdminView, MobileVerifyOTPAdminView
from backoffice.venue import VenuesApi

urlpatterns = [
    path("support/tickets", AdminSupportTicketsAPIView.as_view()),
    path("support/ticket-details", AdminSupportTicketDetailAPIView.as_view()),
    path("support/reply", AdminReplySupportTicketAPIView.as_view()),
    path("support/ticket/update", AdminUpdateSupportTicketStatusAPIView.as_view()),

    path("send-otp", MobileSendOTPAdminView.as_view()),
    path("verify-otp", MobileVerifyOTPAdminView.as_view()),

    path("sports", SportsApi.as_view()),
    path("banners",BannersApi.as_view()),
    path("banners/<uuid:banner_id>",BannersApi.as_view()),
    path("venues", VenuesApi.as_view()),
    path("venues/<uuid:venue_id>", VenuesApi.as_view()),

    path("courts", CourtsApi.as_view()),
    path("courts/<uuid:court_id>", CourtsApi.as_view()),

    path("court-media",CourtMediaApi.as_view()),
    path("court-media/<uuid:media_id>",CourtMediaApi.as_view()),


]