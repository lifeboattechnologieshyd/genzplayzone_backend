from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from db.models import Booking
from shared.utils import CustomResponse


class BackofficeBookingListApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search = request.GET.get("search")
        booking_status = request.GET.get("booking_status")
        payment_status = request.GET.get("payment_status")
        venue_id = request.GET.get("venue_id")
        court_id = request.GET.get("court_id")
        booking_date = request.GET.get("booking_date")
        from_date = request.GET.get("from_date")
        to_date = request.GET.get("to_date")
        bookings = (
            Booking.objects
            .select_related(
                "user",
                "court",
                "court__venue",
            ).prefetch_related(
                "slots",
                "court__court_sports",
                "court__court_sports__sport"
            )
            .order_by("-created_at")
        )
        if search:
            bookings = bookings.filter(
                Q(booking_number__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__phone__icontains=search)
            )
        if booking_status:
            bookings = bookings.filter(
                booking_status=booking_status
            )
        if payment_status:
            bookings = bookings.filter(
                payment_status=payment_status
            )
        if venue_id:
            bookings = bookings.filter(
                court__venue_id=venue_id
            )
        if court_id:
            bookings = bookings.filter(
                court_id=court_id
            )
        if booking_date:
            bookings = bookings.filter(
                booking_date=booking_date
            )
        if from_date:
            bookings = bookings.filter(
                booking_date__gte=from_date
            )
        if to_date:
            bookings = bookings.filter(
                booking_date__lte=to_date
            )
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 20))
        start = (page - 1) * page_size
        end = start + page_size
        total_count = bookings.count()
        bookings = bookings[start:end]
        data = []
        for booking in bookings:
            slot_data = []
            for slot in booking.slots.all():
                slot_data.append({
                    "start_time": slot.start_time.strftime("%I:%M %p"),
                    "end_time": slot.end_time.strftime("%I:%M %p"),
                    "price": float(slot.price)
                })
            sports = [
                cs.sport.name
                for cs in booking.court.court_sports.filter(is_active=True)
            ]
            data.append({
                "booking_id": str(booking.id),
                "booking_number": booking.booking_number,
                "customer_name": booking.user.full_name,
                "customer_mobile": booking.user.mobile,
                "venue": booking.court.venue.name,
                "court": booking.court.name,
                "sports": sports,
                "booking_date": booking.booking_date,
                "slots": slot_data,
                "total_amount": float(booking.total_amount),
                "booking_status": booking.booking_status,
                "payment_status": booking.payment_status,
                "created_at": booking.created_at
            })
        return CustomResponse().successResponse(
            data={
                "count": total_count,
                "page": page,
                "page_size": page_size,
                "results": data
            },
            description="Bookings fetched successfully"
        )