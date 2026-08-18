from django.db import models

from db.models import AuditModel, Sport, Venue, UserMaster


class Tournament(AuditModel):

    STATUS_DRAFT = "DRAFT"
    STATUS_OPEN = "OPEN"
    STATUS_FULL = "FULL"
    STATUS_ONGOING = "ONGOING"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_OPEN, "Open"),
        (STATUS_FULL, "Full"),
        (STATUS_ONGOING, "Ongoing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    name = models.CharField(max_length=255)

    sport = models.ForeignKey(
        Sport,
        on_delete=models.CASCADE,
        related_name="tournaments"
    )

    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="tournaments"
    )

    banner = models.CharField(
        max_length=200,
        default=''
    )

    description = models.TextField(
        null=True,
        blank=True
    )

    tournament_date = models.DateField()

    registration_deadline = models.DateTimeField()

    registration_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    max_participants = models.PositiveIntegerField()

    prize_pool = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    rules = models.TextField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT
    )



    def __str__(self):
        return self.name

    @property
    def registered_participants_count(self):
        return self.participants.filter(
            payment_status=TournamentParticipant.PAYMENT_SUCCESS
        ).count()


class TournamentParticipant(AuditModel):

    PAYMENT_PENDING = "PENDING"
    PAYMENT_SUCCESS = "SUCCESS"
    PAYMENT_FAILED = "FAILED"

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, "Pending"),
        (PAYMENT_SUCCESS, "Success"),
        (PAYMENT_FAILED, "Failed"),
    ]
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name="participants"
    )
    user = models.ForeignKey(
        UserMaster,
        on_delete=models.CASCADE,
        related_name="tournament_participations"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_PENDING
    )
    payment_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    registered_at = models.DateTimeField(
        auto_now_add=True
    )
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tournament", "user"],
                name="unique_tournament_participant"
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.tournament}"


class TournamentResult(AuditModel):

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name="results"
    )
    participant = models.OneToOneField(
        TournamentParticipant,
        on_delete=models.CASCADE,
        null=True,
        related_name="result"
    )
    user = models.ForeignKey(
        UserMaster,
        on_delete=models.CASCADE,
        related_name="tournament_results"
    )
    rank = models.PositiveIntegerField()
    points = models.IntegerField(
        default=0
    )
    prize_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tournament", "user"],
                name="unique_tournament_result"
            )
        ]

    def __str__(self):
        return f"{self.tournament} - {self.user}"


#
# class TournamentPayment(AuditModel):
#
#     STATUS_PENDING = "PENDING"
#     STATUS_SUCCESS = "SUCCESS"
#     STATUS_FAILED = "FAILED"
#     STATUS_CANCELLED = "CANCELLED"
#
#     STATUS_CHOICES = (
#         (STATUS_PENDING, "Pending"),
#         (STATUS_SUCCESS, "Success"),
#         (STATUS_FAILED, "Failed"),
#         (STATUS_CANCELLED, "Cancelled"),
#     )
#     participant = models.OneToOneField(
#         TournamentParticipant,
#         on_delete=models.CASCADE,
#         related_name="payment"
#     )
#     payment_gateway = models.CharField(
#         max_length=50,
#         default="PHONEPE"
#     )
#     order_id = models.CharField(
#         max_length=100,
#         unique=True
#     )
#     transaction_id = models.CharField(
#         max_length=150,
#         blank=True,
#         null=True
#     )
#     amount = models.DecimalField(
#         max_digits=10,
#         decimal_places=2
#     )
#     status = models.CharField(
#         max_length=20,
#         choices=STATUS_CHOICES,
#         default=STATUS_PENDING
#     )
#     raw_response = models.JSONField(
#         blank=True,
#         null=True
#     )
#     paid_at = models.DateTimeField(
#         blank=True,
#         null=True
#     )
#     def __str__(self):
#         return self.order_id