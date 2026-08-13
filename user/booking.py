import json
import traceback
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.messages import success
from django.db import transaction
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from db.models import Court, Booking, BookingSlot, CourtPricing, BookingPayment, TournamentParticipant
from shared.clients.phonepe import phone_pe_initate, check_order_status, refund_phonepe, get_phonepe_client, \
    phone_pe_checkout
from shared.clients.sms import send_sms_to_mobile
from shared.utils import CustomResponse, check_slot_availability, calculate_booking_amount, generate_booking_number, \
    validate_booking_datetime, generate_slots


class BookingsApi(APIView):
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

            response = phone_pe_initate(
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
                booking.booking_status = Booking.STATUS_COMPLETED
                now = timezone.now()
                booking.remarks = (
                    f"{booking.remarks or ''}\n"
                    f"User checked in at {now}. Checked in by {user.mobile}."
                )
                booking.updated_at = now
                booking.save()
                # todo:
                checked_in_at = timezone.localtime(timezone.now()).strftime(
                    "%d %b %Y, %I:%M %p"
                )
                vars = f"{booking.user.full_name}|{booking.booking_number}|{booking.court.name}|{checked_in_at}"
                send_sms_to_mobile(vars, booking.user.mobile, 12662)
                return CustomResponse().successResponse(data={
                        "booking_number": booking.booking_number,
                        "booking_status": booking.booking_status,
                    },
               description="Entry Verified. Allow users to enjoy their play time.")
            return CustomResponse().errorResponse(data={},
                                                  description="Something wrong with booking status. Please contact tech support")



class PaymentResult(APIView):
    permission_classes = [IsAuthenticated]


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
            first_slot = BookingSlot.objects.filter(booking=booking).order_by("start_time").first()

            start_time = first_slot.start_time.strftime("%-I %p")
            end_time = first_slot.end_time.strftime("%-I %p")

            slot_text = (
                f"{booking.booking_date.strftime('%d %b %Y')}, "
                f"{start_time}-{end_time}"
            )
            username = "Player" if request.user.full_name is None else request.user.full_name
            var = f"{username}|{booking.booking_number}|{booking.court.name}|{slot_text}|"
            print(var)
            send_sms_to_mobile(var, request.user.mobile, 12663)
            print("SMS Sent successfully")
            # send_push_notification()
            # send_whatsapp()
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
def handle_booking_webhook(booking_payment, raw_body, payload, state):
    booking = booking_payment.booking
    print("Booking ID:", booking.id)
    print("Booking Number:", booking.booking_number)
    if booking_payment.status == BookingPayment.STATUS_SUCCESS and state == "COMPLETED":
        print("Already in SUCCESS Status Duplicate Webhook")
        return CustomResponse().successResponse(
            data={},
            description="Already processed"
        )
    transaction_id = None
    if getattr(payload, "payment_details", None):
        transaction_id = payload.payment_details[0].transaction_id
    print("Transaction ID:", transaction_id)
    booking_payment.order_id = payload.order_id
    booking_payment.transaction_id = transaction_id
    booking_payment.raw_response = json.loads(raw_body)
    # ------------------------------------------------------
    # SUCCESS
    # ------------------------------------------------------
    if state == "COMPLETED":
        print("========== PAYMENT COMPLETED ==========")
        booking.booking_status = Booking.STATUS_CONFIRMED
        booking.payment_status = Booking.PAYMENT_SUCCESS
        booking_payment.status = BookingPayment.STATUS_SUCCESS
        booking_payment.paid_at = timezone.now()
        booking.save(
            update_fields=[
                "booking_status",
                "payment_status",
            ]
        )
        booking_payment.save(
            update_fields=[
                "order_id",
                "transaction_id",
                "status",
                "paid_at",
                "raw_response",
            ]
        )
        print("Booking Confirmed")
    # ------------------------------------------------------
    # FAILED
    # ------------------------------------------------------
    elif state == "FAILED":
        print("========== PAYMENT FAILED ==========")
        booking.booking_status = Booking.STATUS_CANCELLED
        booking.payment_status = Booking.PAYMENT_FAILED
        booking_payment.status = BookingPayment.STATUS_FAILED
        booking.save(
            update_fields=[
                "booking_status",
                "payment_status",
            ]
        )
        booking_payment.save(
            update_fields=[
                "order_id",
                "transaction_id",
                "status",
                "raw_response",
            ]
        )
        print("Booking Cancelled")
    # ------------------------------------------------------
    # PENDING
    # ------------------------------------------------------
    elif state == "PENDING":
        print("========== PAYMENT PENDING ==========")
        booking.booking_status = Booking.STATUS_PENDING_PAYMENT
        booking.payment_status = Booking.PAYMENT_PENDING
        booking_payment.status = BookingPayment.STATUS_PENDING
        booking.save(
            update_fields=[
                "booking_status",
                "payment_status",
            ]
        )
        booking_payment.save(
            update_fields=[
                "order_id",
                "transaction_id",
                "status",
                "raw_response",
            ]
        )
    # ------------------------------------------------------
    # CANCELLED / OTHER
    # ------------------------------------------------------
    else:
        print("========== PAYMENT CANCELLED ==========")
        booking.booking_status = Booking.STATUS_CANCELLED
        booking.payment_status = Booking.PAYMENT_FAILED
        booking_payment.status = BookingPayment.STATUS_CANCELLED
        booking.save(update_fields=["booking_status","payment_status",])
        booking_payment.save(update_fields=["order_id","transaction_id","status","raw_response",])
    print("========== WEBHOOK PROCESSED SUCCESSFULLY ==========")
    return CustomResponse().successResponse(
        data={},
        description="Webhook processed successfully"
    )

def handle_tournament_webhook(payment, raw_body, payload):
    if payment.type != 'TOURNAMENT':
        return CustomResponse().successResponse(
                data={},
                description="Something wrong"
            )
    print("TOURNAMENT Webhook")
    participant = payment.tournament_participant
    if participant.payment_status == TournamentParticipant.PAYMENT_SUCCESS and payload.state == "COMPLETED":
        print("Already in SUCCESS Status Duplicate Webhook")
        return CustomResponse().successResponse(
            data={},
            description="Already processed"
        )
    transaction_id = None
    if getattr(payload, "payment_details", None):
        transaction_id = payload.payment_details[0].transaction_id
    print("Transaction ID:", transaction_id)
    payment.order_id = payload.order_id
    payment.transaction_id = transaction_id
    payment.raw_response = json.loads(raw_body)
    # ------------------------------------------------------
    # SUCCESS
    # ------------------------------------------------------
    if payload.state == "COMPLETED":
        print("========== PAYMENT COMPLETED ==========")
        participant.payment_status = TournamentParticipant.PAYMENT_SUCCESS
        payment.status = BookingPayment.STATUS_SUCCESS
        payment.paid_at = timezone.now()
        participant.save(update_fields=["payment_status",])
        payment.save(update_fields=["order_id","transaction_id","status","paid_at","raw_response"])
        print("Booking Confirmed")
    # ------------------------------------------------------
    # FAILED
    # ------------------------------------------------------
    elif payload.state == "FAILED":
        print("========== PAYMENT FAILED ==========")
        participant.payment_status = TournamentParticipant.PAYMENT_FAILED
        payment.status = BookingPayment.STATUS_FAILED
        participant.save(update_fields=["payment_status",])
        payment.save(update_fields=["order_id","transaction_id","status","raw_response",])
        print("Booking Cancelled")
    # ------------------------------------------------------
    # PENDING
    # ------------------------------------------------------
    elif payload.state == "PENDING":
        print("========== PAYMENT PENDING ==========")
        participant.payment_status = TournamentParticipant.PAYMENT_PENDING
        payment.status = BookingPayment.STATUS_PENDING
        participant.save(update_fields=["payment_status",])
        payment.save(update_fields=["order_id","transaction_id","status","raw_response", ])
    # ------------------------------------------------------
    # CANCELLED / OTHER
    # ------------------------------------------------------
    else:
        print("========== PAYMENT CANCELLED ==========")
        participant.payment_status = TournamentParticipant.PAYMENT_FAILED
        payment.status = BookingPayment.STATUS_CANCELLED
        participant.save(update_fields=["payment_status"])
        payment.save(update_fields=["order_id", "transaction_id", "status", "raw_response", ])
    print("========== WEBHOOK PROCESSED SUCCESSFULLY ==========")
    return CustomResponse().successResponse(
        data={},
        description="Webhook processed successfully"
    )


class PhonePeCallBack(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request):

        print("\n========== PHONEPE WEBHOOK RECEIVED ==========")
        raw_body = request.body.decode("utf-8")
        auth_header = request.headers.get("Authorization")
        print("Authorization:", auth_header)
        print("Raw Body:", raw_body)
        try:
            client = get_phonepe_client()
            callback = client.validate_callback(
                username="lifeboat",
                password="Lifeboat123",
                callback_header_data=auth_header,
                callback_response_data=raw_body,
            )
            print("Webhook Validation Success")
        except Exception as e:
            print("\n========== WEBHOOK VALIDATION FAILED ==========")
            traceback.print_exc()
            #todo: email log.. if any issue, admin should get an email
            return CustomResponse().successResponse(
                data={},
                description="Ignored"
            )
        # Validation callback
        if not callback.payload:
            print("Validation Callback Received")
            return CustomResponse().successResponse(
                data={},
                description="Validation Success"
            )
        payload = callback.payload
        event = callback.event
        print("Event:", event)
        # # ======================================================
        # # REFUND EVENTS
        # # ======================================================
        # if event in (
        #     "pg.refund.completed",
        #     "pg.refund.failed",
        # ):
        #
        #     merchant_order_id = payload.original_merchant_order_id
        #
        #     print("Refund Event")
        #     print("Original Merchant Order ID:", merchant_order_id)
        #     print("Refund ID:", payload.refund_id)
        #     print("Merchant Refund ID:", payload.merchant_refund_id)
        #     print("State:", payload.state)
        #
        #     booking_payment = BookingPayment.objects.select_related(
        #         "booking"
        #     ).filter(
        #         booking_id=merchant_order_id
        #     ).first()
        #
        #     if booking_payment is None:
        #         print("Booking Payment Not Found")
        #         return CustomResponse().successResponse(
        #             data={},
        #             description="Booking payment not found"
        #         )
        #
        #
        #     booking = booking_payment.booking
        #     booking_payment.raw_response = json.loads(raw_body)
        #     if payload.state == "COMPLETED":
        #         print("Refund Completed")
        #         booking.booking_status = Booking.STATUS_CANCELLED
        #         booking.payment_status = Booking.PAYMENT_FAILED
        #         booking.save(
        #             update_fields=[
        #                 "booking_status",
        #                 "payment_status",
        #             ]
        #         )
        #
        #         booking_payment.save(
        #             update_fields=[
        #                 "raw_response",
        #             ]
        #         )
        #
        #     else:
        #
        #         print("Refund Failed")
        #
        #         booking_payment.save(
        #             update_fields=[
        #                 "raw_response",
        #             ]
        #         )
        #
        #     return CustomResponse().successResponse(
        #         data={},
        #         description="Refund webhook processed successfully"
        #     )

        # ======================================================
        # PAYMENT EVENTS
        # ======================================================
        merchant_order_id = payload.merchant_order_id
        gateway_order_id = payload.order_id
        state = payload.state
        print("Merchant Order ID:", merchant_order_id)
        print("Gateway Order ID:", gateway_order_id)
        print("State:", state)
        booking_payment = BookingPayment.objects.select_related(
            "booking"
        ).filter(
            booking_id=merchant_order_id
        ).first()
        if booking_payment:
            return handle_booking_webhook(booking_payment, raw_body, payload, state)
        else:
            print("will try to see tournament record")
            payment = BookingPayment.objects.select_related(
                "booking"
            ).filter(
                tournament_participant=merchant_order_id
            ).first()
            if payment:
                return handle_tournament_webhook(payment, raw_body, payload)
            else:
                return CustomResponse().successResponse(
                    data={},
                    description="Booking or tournament payment not found"
                )


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



class CancelBookingAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        booking_id = request.data.get("booking_id")
        reason = request.data.get("reason", "").strip()
        user = request.user
        if not booking_id:
            return CustomResponse().errorResponse(
                data={},
                description="Booking ID is required."
            )

        try:
            with transaction.atomic():
                booking = (
                    Booking.objects
                    .select_for_update()
                    .select_related("user", "court")
                    .filter(id=booking_id)
                    .first()
                )

                if not booking:
                    return CustomResponse().errorResponse(
                        data={},
                        description="Booking not found."
                    )

                is_booking_owner = booking.user_id == user.id

                if not is_booking_owner:
                    print(f"You do not have permission to cancel this booking. == {user.id}")

                    return CustomResponse().errorResponse(
                        data={},
                        description="You do not have permission to cancel this booking."
                    )

                if booking.booking_status == Booking.STATUS_CANCELLED:
                    print("This booking is already cancelled.")

                    return CustomResponse().errorResponse(
                        data={},
                        description="This booking is already cancelled."
                    )

                if booking.booking_status == Booking.STATUS_EXPIRED:
                    print("This booking has already expired.")

                    return CustomResponse().errorResponse(
                        data={},
                        description="This booking has already expired."
                    )

                if booking.booking_status in [
                    Booking.STATUS_COMPLETED,
                    Booking.STATUS_NO_SHOW,
                ]:
                    print("This booking cannot be cancelled. bcz its in complteted or no show")
                    return CustomResponse().errorResponse(
                        data={},
                        description="This booking cannot be cancelled."
                    )

                # Pending payments can be cancelled, but no refund applies.
                if booking.booking_status == Booking.STATUS_PENDING_PAYMENT:
                    booking.booking_status = Booking.STATUS_CANCELLED
                    booking.cancelled_at = timezone.now()
                    booking.cancelled_by = user
                    booking.cancellation_reason = reason
                    booking.refund_amount = Decimal("0.00")
                    booking.refund_status = Booking.REFUND_NOT_APPLICABLE
                    booking.expires_at = timezone.now()
                    booking.save()
                    print("Pending booking cancelled successfully.")

                    return CustomResponse().successResponse(
                        data={
                            "booking_number": booking.booking_number,
                            "refund_amount": "0.00",
                            "refund_status": booking.refund_status,
                        },
                        description="Pending booking cancelled successfully."
                    )

                if booking.booking_status != Booking.STATUS_CONFIRMED:
                    print(f"This booking cannot be cancelled. as its not in confirmed status=={booking.booking_status}")

                    return CustomResponse().errorResponse(
                        data={},
                        description="This booking cannot be cancelled."
                    )

                first_slot = (
                    BookingSlot.objects
                    .filter(booking=booking)
                    .order_by("start_time")
                    .first()
                )

                if not first_slot:
                    print("No slots found for this booking.")
                    return CustomResponse().errorResponse(
                        data={},
                        description="No slots found for this booking."
                    )

                slot_start_datetime = datetime.combine(
                    booking.booking_date,
                    first_slot.start_time
                )

                slot_start_datetime = timezone.make_aware(
                    slot_start_datetime,
                    timezone.get_current_timezone()
                )

                now = timezone.now()

                if now >= slot_start_datetime:
                    print("A started booking cannot be cancelled")

                    return CustomResponse().errorResponse(
                        data={},
                        description="A started booking cannot be cancelled."
                    )

                remaining_time = slot_start_datetime - now

                # Exactly 6 hours or more = 80% refund.
                if remaining_time >= timedelta(hours=6):
                    refund_amount = (
                        booking.total_amount * Decimal("0.80")
                    ).quantize(
                        Decimal("0.01"),
                        rounding=ROUND_HALF_UP
                    )
                    refund_status = Booking.REFUND_PENDING
                    description = (
                        "Booking cancelled. Your 80% refund will be processed shortly."
                    )
                else:
                    refund_amount = Decimal("0.00")
                    refund_status = Booking.REFUND_NOT_APPLICABLE
                    description = (
                        "Booking cancelled. No refund is available within 6 hours "
                        "of the slot start time."
                    )

                booking.booking_status = Booking.STATUS_CANCELLED
                booking.cancelled_at = now
                booking.cancelled_by = user
                booking.cancellation_reason = reason
                booking.refund_amount = refund_amount
                booking.refund_status = refund_status
                booking.remarks = (
                    f"{booking.remarks or ''}\n"
                    f"Cancelled at {now} by {user.mobile}. "
                    f"Refund amount: {refund_amount}."
                )
                booking.save()
            # Phone pe Refund.
            if refund_amount > 0:
                print(f"initiating phone pe refund {refund_amount}")
                response = refund_phonepe(booking.id, refund_amount)
                booking.refund_status = response.state
                booking.save()
            return CustomResponse().successResponse(
                data={
                    "booking_id": str(booking.id),
                    "booking_number": booking.booking_number,
                    "booking_status": booking.booking_status,
                    "refund_amount": str(booking.refund_amount),
                    "refund_status": booking.refund_status,
                },
                description=description
            )

        except Exception as error:
            return CustomResponse().errorResponse(
                data={},
                description=f"Unable to cancel booking. Please try again. {error}"
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
            print("\n========== PHONEPE CHECKOUT ==========")
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
                    order_id=response["order_id"],
                    amount=booking.total_amount,
                    status=BookingPayment.STATUS_PENDING,
                    raw_response=response,
                )

                print("Booking Payment Created")
                print("Payment ID:", payment.id)
                print("PhonePe Order ID:", payment.order_id)
                print("Payment Amount:", payment.amount)
                print("Payment Status:", payment.status)

                response_data = {
                    "booking_id": str(booking.id),
                    "booking_number": booking.booking_number,
                    "booking_status": booking.booking_status,
                    "payment_status": booking.payment_status,
                    "total_amount": booking.total_amount,
                    "merchant_order_id": str(booking.id),
                    "phonepe_order_id": response["order_id"],
                    "redirect_url": response["redirect_url"],
                    "state": response["state"],
                    "expire_at": response["expire_at"],

                }

                print("\n========== SUCCESS RESPONSE ==========")
                print(response_data)

                return CustomResponse().successResponse(
                    data=response_data,
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
                    "expires_at",
                ]
            )

            print("Booking Updated As Payment Failed")

            return CustomResponse().errorResponse(
                data={},
                description=str(e)
            )

