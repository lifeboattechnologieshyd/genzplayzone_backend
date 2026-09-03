
from django.db.models import Q



from shared.clients.sms import send_sms_to_mobile

import traceback

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from datetime import datetime, timedelta
from django.utils import timezone

from db.models import Court, Booking, BookingSlot, BookingPayment, UserMaster, CourtPricing
from shared.clients.phonepe import phone_pe_checkout, refund_phonepe
from shared.utils import CustomResponse, validate_booking_datetime, check_slot_availability, calculate_booking_amount, \
    generate_booking_number, generate_slots


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


    @transaction.atomic
    def post(self, request):

        user_id = request.data.get("user_id")
        court_id = request.data.get("court_id")
        booking_date = request.data.get("booking_date")
        slots = request.data.get("slots", [])
        payment_method = request.data.get("payment_method", "CASH")

        if not user_id:
            return CustomResponse().errorResponse(
                data={},
                description="User is required"
            )

        if not court_id:
            return CustomResponse().errorResponse(
                data={},
                description="Court is required"
            )

        if not booking_date:
            return CustomResponse().errorResponse(
                data={},
                description="Booking date is required"
            )

        if not slots:
            return CustomResponse().errorResponse(
                data={},
                description="Please select slots"
            )

        try:
            user = UserMaster.objects.get(
                id=user_id,
                is_active=True
            )
        except UserMaster.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="User not found"
            )

        try:
            court = Court.objects.get(
                id=court_id,
                is_active=True
            )
        except Court.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Court not found"
            )

        try:
            booking_date = datetime.strptime(
                booking_date,
                "%Y-%m-%d"
            ).date()
        except Exception:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid booking date"
            )
        try:
            validate_booking_datetime(
                booking_date,
                slots
            )

            check_slot_availability(
                court,
                booking_date,
                slots
            )

            total_amount, slot_prices = calculate_booking_amount(
                court,
                booking_date,
                slots
            )

            booking = Booking.objects.create(
                booking_number=generate_booking_number(),
                user=user,
                court=court,
                booking_date=booking_date,
                total_amount=total_amount,
                booking_status=Booking.STATUS_CONFIRMED,
                payment_status=Booking.PAYMENT_SUCCESS
            )

            for slot in slot_prices:

                BookingSlot.objects.create(
                    booking=booking,
                    start_time=slot["start_time"],
                    end_time=slot["end_time"],
                    price=slot["price"]
                )

            BookingPayment.objects.create(
                booking=booking,
                payment_gateway=payment_method,
                order_id=f"OFFLINE-{booking.booking_number}",
                amount=booking.total_amount,
                status=BookingPayment.STATUS_SUCCESS,
                paid_at=timezone.now(),
                raw_response={
                    "created_by": str(request.user.id),
                    "type": "BACKOFFICE"
                }
            )

            first_slot = BookingSlot.objects.filter(booking=booking).order_by("start_time").first()

            start_time = first_slot.start_time.strftime("%-I %p")
            end_time = first_slot.end_time.strftime("%-I %p")

            slot_text = (
                f"{booking.booking_date.strftime('%d %b %Y')}, "
                f"{start_time}-{end_time}"
            )
            # TODO: send push and email n whatsapp too.
            username = "Player" if user.full_name is None else user.full_name
            var = f"{username}|{booking.booking_number}|{booking.court.name}|{slot_text}|"
            print(var)
            send_sms_to_mobile(var, user.mobile, 12663)
            print("SMS Sent successfully")
            # send_push_notification()
            # send_whatsapp()
            # send_email()

            return CustomResponse().successResponse(
                data={
                    "booking_id": str(booking.id),
                    "booking_number": booking.booking_number,
                    "total_amount": booking.total_amount
                },
                description="Booking created successfully"
            )

        except Exception as e:
            return CustomResponse().errorResponse(
                data={},
                description=str(e)
            )


class CourtAvailabilityApi(APIView):
    permission_classes = [IsAuthenticated]

    def slot_status(self, booking_date, slot, booked):
        status = Booking.SLOT_STATUS_AVAILABLE
        today = timezone.localdate()
        now = timezone.localtime()
        print(now)
        print(slot["start_time"])
        if (slot["start_time"],slot["end_time"]) in booked:
            status = Booking.SLOT_STATUS_BOOKED
        else:
            if booking_date < today:
                status = Booking.SLOT_STATUS_PAST
            elif booking_date == today:
                print("date is today so comparing times")
                slot_datetime = datetime.combine(
                    booking_date,
                    slot["start_time"]
                )
                now_datetime = now.replace(
                    tzinfo=None
                )
                print(now_datetime)
                print(slot_datetime)
                if slot_datetime <= now_datetime + timedelta(minutes=15):
                    status = Booking.SLOT_STATUS_PAST
        return status

    def get(self, request):
        court_id = request.GET.get("court_id")
        booking_date = request.GET.get("booking_date")
        if not court_id:
            return CustomResponse().errorResponse(
                data={},
                description="Court is required"
            )
        if not booking_date:
            return CustomResponse().errorResponse(
                data={},
                description="Booking date is required"
            )
        try:
            court = Court.objects.get(
                id=court_id,
                is_active=True
            )
        except Court.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Court not found"
            )
        try:
            booking_date = datetime.strptime(
                booking_date,
                "%Y-%m-%d"
            ).date()
        except Exception:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid booking date."
            )
        day = booking_date.strftime(
            "%A"
        ).upper()
        pricing_list = CourtPricing.objects.filter(
            court=court,
            day=day,
            is_active=True
        ).order_by(
            "start_time"
        )
        booked_slots = BookingSlot.objects.filter(
            booking__court=court,
            booking__booking_date=booking_date
        ).filter(
            Q(
                booking__booking_status=Booking.STATUS_CONFIRMED
            ) |
            Q(
                booking__booking_status=Booking.STATUS_PENDING_PAYMENT,
                booking__expires_at__gt=timezone.now()
            )
        )
        booked = set()
        for slot in booked_slots:
            booked.add(
                (
                    slot.start_time,
                    slot.end_time
                )
            )
        slots = []
        for pricing in pricing_list:
            generated_slots = generate_slots(
                pricing,
                court.slot_duration_minutes
            )
            for slot in generated_slots:
                available = (
                    slot["start_time"],
                    slot["end_time"]
                ) not in booked
                # Default
                status = self.slot_status(booking_date, slot, booked)
                slots.append({
                    "start_time": slot["start_time"].strftime("%H:%M"),
                    "end_time": slot["end_time"].strftime("%H:%M"),
                    "price": slot["price"],
                    "available": available,
                    "status": status
                })
        return CustomResponse().successResponse(
            data={
                "court": {
                    "id": str(court.id),
                    "name": court.name
                },
                "booking_date": booking_date,
                "slots": slots
            },
            description="Availability fetched successfully"
        )


class BackofficeBookingCancelApi(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):

        reason = request.data.get("reason", "").strip()

        if not reason:
            return CustomResponse().errorResponse(
                data={},
                description="Cancellation reason is required."
            )

        try:
            # -----------------------------------------
            # Get ONE specific booking
            # -----------------------------------------
            booking = (
                Booking.objects
                .select_related("user", "court")
                .select_for_update()
                .get(id=booking_id)
            )

        except Booking.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Booking not found."
            )

        # -----------------------------------------
        # Check booking status
        # -----------------------------------------
        if booking.booking_status == Booking.STATUS_CANCELLED:
            return CustomResponse().errorResponse(
                data={},
                description="Booking is already cancelled."
            )

        if booking.booking_status != Booking.STATUS_CONFIRMED:
            return CustomResponse().errorResponse(
                data={},
                description="Only confirmed bookings can be cancelled."
            )

        # -----------------------------------------
        # Get successful payment
        # -----------------------------------------
        payment = (
            BookingPayment.objects
            .filter(
                booking=booking,
                status=BookingPayment.STATUS_SUCCESS
            )
            .order_by("-created_at")
            .first()
        )

        if not payment:
            return CustomResponse().errorResponse(
                data={},
                description="Successful payment not found for this booking."
            )

        # -----------------------------------------
        # Check payment gateway
        # -----------------------------------------
        if payment.payment_gateway != "PHONEPE":
            return CustomResponse().errorResponse(
                data={},
                description="Refund is supported only for PhonePe payments."
            )

        # -----------------------------------------
        # Refund amount
        # -----------------------------------------
        refund_amount = booking.total_amount

        try:

            # -----------------------------------------
            # Initiate PhonePe refund
            # -----------------------------------------
            refund_response = refund_phonepe(
                payment.order_id,
                refund_amount
            )

            print("PhonePe Refund Response:", refund_response)

        except Exception as exc:

            traceback.print_exc()

            return CustomResponse().errorResponse(
                data={},
                description=f"Refund initiation failed: {str(exc)}"
            )



        refund_state = getattr(
            refund_response,
            "state",
            None
        )

        if refund_state == "COMPLETED":
            refund_status = Booking.REFUND_SUCCESS
            payment_status = Booking.PAYMENT_REFUNDED

        elif refund_state in ["PENDING", "PROCESSING"]:
            refund_status = Booking.REFUND_PENDING
            payment_status = Booking.PAYMENT_SUCCESS

        else:
            refund_status = Booking.REFUND_FAILED
            payment_status = Booking.PAYMENT_SUCCESS

        # -----------------------------------------
        # Update booking
        # -----------------------------------------

        try:

            with transaction.atomic():

                booking.booking_status = Booking.STATUS_CANCELLED
                booking.cancelled_at = timezone.now()
                booking.cancelled_by = request.user
                booking.cancellation_reason = reason
                booking.refund_amount = refund_amount
                booking.refund_status = refund_status
                booking.payment_status = payment_status

                booking.save(
                    update_fields=[
                        "booking_status",
                        "cancelled_at",
                        "cancelled_by",
                        "cancellation_reason",
                        "refund_amount",
                        "refund_status",
                        "payment_status",
                    ]
                )

        except Exception as exc:

            traceback.print_exc()

            return CustomResponse().errorResponse(
                data={},
                description=str(exc)
            )

        return CustomResponse().successResponse(
            data={
                "booking_id": str(booking.id),
                "booking_number": booking.booking_number,
                "customer_name": booking.user.full_name,
                "booking_status": booking.booking_status,
                "payment_status": booking.payment_status,
                "refund_amount": booking.refund_amount,
                "refund_status": booking.refund_status,
                "cancellation_reason": booking.cancellation_reason,
                "cancelled_at": booking.cancelled_at,
            },
            description="Booking cancelled successfully."
        )

