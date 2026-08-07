from django.urls import path

from backoffice.Bookings import BackofficeBookingListApi, CourtAvailabilityApi
from backoffice.banners import BannersApi
from backoffice.courts import CourtsApi, CourtMediaApi, CourtPricingsApi
from backoffice.promocode import PromocodeApi
from backoffice.sports import SportsApi
from backoffice.support import AdminSupportTicketsAPIView, AdminSupportTicketDetailAPIView, \
    AdminReplySupportTicketAPIView, AdminUpdateSupportTicketStatusAPIView
from backoffice.user import MobileSendOTPAdminView, MobileVerifyOTPAdminView, BackofficeDashboardApi
from backoffice.users import BackofficeUsersApi, BackofficeCreateUsersApi, BackofficeVerifyUserApi
from backoffice.venue import VenuesApi, AmenitiesApi, VenueAmenitiesApi

urlpatterns = [
    path("support/tickets", AdminSupportTicketsAPIView.as_view()),
    path("support/ticket-details", AdminSupportTicketDetailAPIView.as_view()),
    path("support/reply", AdminReplySupportTicketAPIView.as_view()),
    path("support/ticket/update", AdminUpdateSupportTicketStatusAPIView.as_view()),

    path("send-otp", MobileSendOTPAdminView.as_view()),
    path("verify-otp", MobileVerifyOTPAdminView.as_view()),

    path("sports", SportsApi.as_view()),
    path("sports/<uuid:sport_id>", SportsApi.as_view()),

    path("banners",BannersApi.as_view()),
    path("banners/<uuid:banner_id>",BannersApi.as_view()),

    path("venues", VenuesApi.as_view()),
    path("venues/<uuid:venue_id>", VenuesApi.as_view()),

    path("amenities", AmenitiesApi.as_view()),
    path("amenities/<uuid:amenity_id>", AmenitiesApi.as_view()),
    path("venue-amenities",VenueAmenitiesApi.as_view()),
    path("venue-amenities/<uuid:venue_amenity_id>",VenueAmenitiesApi.as_view()),

    path("courts", CourtsApi.as_view()),
    path("courts/<uuid:court_id>", CourtsApi.as_view()),

    path("court-media",CourtMediaApi.as_view()),
    path("court-media/<uuid:media_id>",CourtMediaApi.as_view()),

    path("court-pricing", CourtPricingsApi.as_view()),
    path("court-pricing/<uuid:pricing_id>", CourtPricingsApi.as_view()),
    path("promo-codes", PromocodeApi.as_view()),


    path("bookings", BackofficeBookingListApi.as_view()),
    path("available-slots", CourtAvailabilityApi.as_view()),
    path("users", BackofficeUsersApi.as_view()),
    path("user/create", BackofficeCreateUsersApi.as_view()),
    path("user/verify", BackofficeVerifyUserApi.as_view()),
    path("dashboard", BackofficeDashboardApi.as_view()),


]