
from django.db.models import Q



from shared.clients.sms import send_sms_to_mobile

import traceback

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from datetime import datetime, timedelta
from django.utils import timezone

from db.models import Court, Booking, BookingSlot, BookingPayment, UserMaster, CourtPricing
from shared.clients.phonepe import phone_pe_checkout
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




class BookingsApiView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("\n================ BOOKING API START ================")
        print("User:", request.user.id)
        print("Request Data:", request.data)

        court_id = request.data.get("court_id")
        booking_date = request.data.get("booking_date")
        slots = request.data.get("slots", [])

        print("Court ID:", court_id)
        print("Booking Date:", booking_date)
        print("Slots:", slots)

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
                description="Please select at least one slot"
            )

        try:
            booking_date = datetime.strptime(
                booking_date,
                "%Y-%m-%d"
            ).date()

            print("Parsed Booking Date:", booking_date)

        except Exception as e:
            print("Date Parsing Error:", str(e))
            return CustomResponse().errorResponse(
                data={},
                description="Invalid booking date"
            )

        try:
            print("\n========== VALIDATING BOOKING ==========")

            validate_booking_datetime(booking_date, slots)
            print("Booking Date Validation Success")

            with transaction.atomic():

                print("\nFetching Court...")

                court = Court.objects.select_for_update().get(
                    id=court_id,
                    is_active=True
                )

                print("Court Found:", court.id)

                print("Checking Slot Availability...")

                check_slot_availability(
                    court,
                    booking_date,
                    slots
                )

                print("Slots Available")

                print("Calculating Booking Amount...")

                total_amount, slot_prices = calculate_booking_amount(
                    court,
                    booking_date,
                    slots
                )

                print("Total Amount:", total_amount)
                print("Amount Type:", type(total_amount))
                print("Slot Prices:", slot_prices)

                print("Creating Booking...")

                booking = Booking.objects.create(
                    booking_number=generate_booking_number(),
                    user=request.user,
                    court=court,
                    booking_date=booking_date,
                    total_amount=total_amount,
                    booking_status=Booking.STATUS_PENDING_PAYMENT,
                    payment_status=Booking.PAYMENT_PENDING,
                    expires_at=timezone.now() + timedelta(minutes=10),
                )

                print("Booking Created")
                print("Booking ID:", booking.id)
                print("Booking Number:", booking.booking_number)

                print("Creating Booking Slots...")

                BookingSlot.objects.bulk_create([
                    BookingSlot(
                        booking=booking,
                        start_time=slot["start_time"],
                        end_time=slot["end_time"],
                        price=slot["price"],
                    )
                    for slot in slot_prices
                ])

                print("Booking Slots Created")

        except Court.DoesNotExist:
            print("Court Not Found")
            return CustomResponse().errorResponse(
                data={},
                description="Court not found"
            )

        except Exception as exc:
            print("\n========== BOOKING CREATION ERROR ==========")
            traceback.print_exc()

            return CustomResponse().errorResponse(
                data={},
                description=str(exc)
            )

        try:
            print("\n========== PHONEPE PAYMENT ==========")
            print("Booking ID:", booking.id)
            print("Booking Total Amount:", booking.total_amount)
            print("Passing Total Amount:", total_amount)

            response = phone_pe_checkout(
                booking.id,
                total_amount
            )

            print("\n========== PHONEPE RESPONSE ==========")
            print(response)

            with transaction.atomic():

                print("Creating Booking Payment...")

                payment = BookingPayment.objects.create(
                    booking=booking,
                    payment_gateway="PHONEPE",
                    order_id=response.order_id,
                    amount=booking.total_amount,
                    status=BookingPayment.STATUS_PENDING,
                    raw_response=response.__dict__,
                )

                print("Booking Payment Created")
                print("Payment ID:", payment.id)
                print("Payment Amount:", payment.amount)
                print("Payment Status:", payment.status)

                res = {
                    "token": response.token,
                    "order_id": response.order_id,
                    "state": response.state,
                    "expire_at": response.expire_at,
                }

                print("\n========== SUCCESS RESPONSE ==========")
                print(res)

                return CustomResponse().successResponse(
                    data={
                        "booking_id": str(booking.id),
                        "booking_number": booking.booking_number,
                        "total_amount": booking.total_amount,
                        **res
                    },
                    description="Booking created successfully"
                )

        except Exception as e:

            print("\n========== PHONEPE PAYMENT ERROR ==========")
            print("Exception Type:", type(e).__name__)
            print("Exception:", str(e))
            traceback.print_exc()

            booking.payment_status = Booking.PAYMENT_FAILED
            booking.expires_at = timezone.now()

            booking.save(
                update_fields=[
                    "payment_status",
                    "expires_at"
                ]
            )

            print("Booking Updated As Payment Failed")

            return CustomResponse().errorResponse(
                data={},
                description=str(e)
            )

    def get(self, request):
        booking_type = request.GET.get("type")
        id = request.GET.get("id")
        booking_number = request.GET.get("booking_number")
        bookings = Booking.objects.filter(
            user=request.user,
            is_active=True
        ).select_related(
            "court",
            "court__venue"
        ).prefetch_related(
            "slots"
        )
        today = timezone.localdate()
        if booking_type == "UPCOMING":
            bookings = bookings.filter(
                booking_date__gte=today,
                booking_status__in=[
                    Booking.STATUS_CONFIRMED
                ]
            )
        elif booking_type == "COMPLETED":
            bookings = bookings.filter(
                booking_status=Booking.STATUS_COMPLETED
            )
        elif booking_type == "CANCELLED":
            bookings = bookings.filter(
                booking_status=Booking.STATUS_CANCELLED
            )
        if id and booking_number:
            bookings = bookings.filter(id=id, booking_number=booking_number)
        bookings = bookings.order_by(
            "-booking_date",
            "-created_at"
        )
        data = []
        for booking in bookings:
            slots = []
            for slot in booking.slots.all():
                slots.append({
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": slot.end_time.strftime("%H:%M")
                })
            data.append({
                "id": str(booking.id),
                "booking_number": booking.booking_number,
                "booking_date": booking.booking_date,
                "court": {
                    "id": str(booking.court.id),
                    "name": booking.court.name,
                    "cover_image": booking.court.cover_image
                },
                "venue": {
                    "id": str(booking.court.venue.id),
                    "name": booking.court.venue.name,
                    "address": booking.court.venue.address
                },
                "slots": slots,
                "total_amount": booking.total_amount,
                "booking_status": booking.booking_status,
                "payment_status": booking.payment_status
            })
        return CustomResponse().successResponse(
            data={
                "bookings": data
            },
            description="Bookings fetched successfully"
        )
