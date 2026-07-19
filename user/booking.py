from datetime import datetime, timedelta

from django.contrib.messages import success
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from db.models import Court, Booking, BookingSlot, CourtPricing, BookingPayment
from shared.clients.phonepe import phone_pe_initate, check_order_status
from shared.utils import CustomResponse, check_slot_availability, calculate_booking_amount, generate_booking_number, \
    validate_booking_datetime, generate_slots


class BookingsApi(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        court_id = request.data.get("court_id")
        booking_date = request.data.get("booking_date")
        slots = request.data.get("slots", [])
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
        except Exception:
            return CustomResponse().errorResponse(
                data={},
                description="Invalid booking date"
            )

        try:
            validate_booking_datetime(booking_date,slots)
            with transaction.atomic():
                court = Court.objects.select_for_update().get(
                    id=court_id,
                    is_active=True
                )
                check_slot_availability(court, booking_date,slots)
                total_amount, slot_prices = calculate_booking_amount(court, booking_date, slots)
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
                BookingSlot.objects.bulk_create([
                    BookingSlot(
                        booking=booking,
                        start_time=slot["start_time"],
                        end_time=slot["end_time"],
                        price=slot["price"],
                    )
                    for slot in slot_prices
                ])
        except Court.DoesNotExist:
            return CustomResponse().errorResponse(
                data={}, description="Court not found"
            )
        except Exception as exc:
            return CustomResponse().errorResponse(
                data={}, description=str(exc)
            )
        try:
            response = phone_pe_initate(booking.id)
            with transaction.atomic():
                BookingPayment.objects.create(
                    booking=booking,
                    payment_gateway="PHONEPE",
                    order_id=response.order_id,
                    amount=booking.total_amount,
                    status=BookingPayment.STATUS_PENDING,
                    raw_response=response.__dict__
                )
                res = {
                    "token": response.token,
                    "order_id": response.order_id,
                    "state": response.state,
                    "expire_at": response.expire_at,
                }
                print("Payment Initiate call =====")
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
            booking.payment_status = Booking.PAYMENT_FAILED
            booking.expires_at = timezone.now()
            booking.save(update_fields=["payment_status", "expires_at"])
            return CustomResponse().errorResponse(
                data={},
                description="Unable to initiate payment. Please try again."
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
                    Booking.STATUS_PENDING_PAYMENT,
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

class CheckInAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user=request.user
        booking_number = request.data.get("booking_number")
        booking_id = request.data.get("id")
        if not booking_number:
            return CustomResponse().errorResponse(
                data={}, description="Booking number is required."
            )
        if not booking_id:
            return CustomResponse().errorResponse(
                data={}, description="Booking id is required."
            )

        if 'admin' not in user.user_role:
            return CustomResponse().errorResponse(data={}, description="You don't have permission to access this")
        with transaction.atomic():
            booking = Booking.objects.select_for_update().filter(id=booking_id, booking_number=booking_number).first()
            if not booking:
                return CustomResponse().errorResponse(data={}, description="Invalid Booking Details")
            if booking.booking_status == Booking.STATUS_COMPLETED:
                return CustomResponse().errorResponse(data={}, description="This Booking is already completed")
            if booking.booking_status == Booking.STATUS_CONFIRMED:
                booking.booking_status = Booking.STATUS_CHECKIN
                now = timezone.now()
                booking.remarks = (
                    f"{booking.remarks or ''}\n"
                    f"User checked in at {now}. Checked in by {user.mobile}."
                )
                booking.updated_at = now
                booking.save()
                # todo:
                # send an sms.
                return CustomResponse().successResponse(data={
                        "booking_number": booking.booking_number,
                        "booking_status": booking.booking_status,
                    },
               description="Entry Verified. Allow users to enjoy their play time.")
            return CustomResponse().errorResponse(data={},
                                                  description="Something wrong with booking status. Please contact tech support")



class PaymentResult(APIView):

    @transaction.atomic
    def post(self, request):
        print("phone pe result api")
        print(request.data)
        booking_id = request.data.get("booking_id")
        if not booking_id:
            return CustomResponse().errorResponse(
                data={},
                description="Booking id is required"
            )
        try:
            booking = Booking.objects.select_for_update().get(
                id=booking_id,
                user=request.user
            )
        except Booking.DoesNotExist:
            return CustomResponse().errorResponse(
                data={},
                description="Booking not found"
            )
        if booking.booking_status == Booking.STATUS_CONFIRMED:
            return CustomResponse().successResponse(
                data={
                    "booking_status": booking.booking_status,
                    "payment_status": booking.payment_status
                },
                description="Payment already verified"
            )
        try:
            response = check_order_status(booking.id)
        except Exception as e:
            return CustomResponse().errorResponse(
                data={},
                description=str(e)
            )
        payment = BookingPayment.objects.filter(
            booking=booking
        ).first()
        if response.state == "COMPLETED":
            booking.booking_status = Booking.STATUS_CONFIRMED
            booking.payment_status = Booking.PAYMENT_SUCCESS
            booking.save()
            if payment:
                payment.status = BookingPayment.STATUS_SUCCESS
                txns = response.payment_details
                completed_payments = [
                    payment
                    for payment in txns
                    if payment.state == "COMPLETED"
                ]
                txn = completed_payments[0]
                payment.transaction_id = txn.transaction_id
                payment.paid_at = timezone.now()
                payment.save()
            # TODO
            # send_push_notification()
            # send_whatsapp()
            # send_sms()
            # send_email()
            return CustomResponse().successResponse(
                data={
                    "booking_status": booking.booking_status,
                    "payment_status": booking.payment_status,
                    "id":booking.id,
                    "number":booking.booking_number
                },
                description="Payment successful"
            )
        elif response.state == "FAILED":

            booking.booking_status = Booking.STATUS_CANCELLED
            booking.payment_status = Booking.PAYMENT_FAILED
            booking.save()

            if payment:
                payment.status = BookingPayment.STATUS_FAILED
                payment.raw_response = response.__dict__
                payment.save()

            return CustomResponse().errorResponse(
                data={
                    "booking_status": booking.booking_status,
                    "payment_status": booking.payment_status
                },
                description="Payment failed"
            )
        else:
            return CustomResponse().successResponse(
                data={
                    "booking_status": booking.booking_status,
                    "payment_status": booking.payment_status,
                    "state": response.state
                },
                description="Payment is pending"
            )


class PhonePeCallBack(APIView):
    def post(self, request):
        print("phone pe webhook configured")
        print(request.data)
        return CustomResponse().successResponse(data={}, description="Success")


from datetime import datetime

from django.db.models import Q
from django.utils import timezone


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