import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from crum import get_current_request



class TimeAuditModel(models.Model):
    """To path when the record was created and last modified"""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Modified At")

    class Meta:
        abstract = True


class UserAuditModel(models.Model):
    """To path when the record was created and last modified"""

    created_by = models.CharField(
        max_length=255,
        verbose_name="Created By",
        null=True,
    )
    updated_by = models.CharField(
        max_length=255,
        verbose_name="Updated By",
        null=True,
    )

    class Meta:
        abstract = True


class AuditModel(TimeAuditModel, UserAuditModel):
    """To path when the record was created and last modified"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        request = get_current_request()
        if request and hasattr(request, "user"):
            if not self.created_by:
                self.created_by = str(request.user.id)
            self.updated_by = str(request.user.id)

        super().save(*args, **kwargs)

class CustomUserManager(BaseUserManager):
    def create_user(self, mobile, password="password", **extra_fields):
        if not mobile:
            raise ValueError("The Mobile Number must be set")



        user = self.model(mobile=mobile, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class UserMaster(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mobile = models.BigIntegerField(
        validators=[MinValueValidator(1000000000), MaxValueValidator(9999999999)], unique=True
    )
    is_mobile_verified = models.BooleanField(default=False)
    full_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    gender = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    email = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    dob = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    profile_image = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )
    user_role = ArrayField(models.CharField(max_length=50, ), blank=True, null=True)
    is_active = models.BooleanField(default=True)
    referral_code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        null=True,
        blank=True
    )

    coins = models.PositiveIntegerField(
        default=0
    )
    last_login_at = models.DateTimeField(
        null=True,
        blank=True
    )
    created_by = models.CharField(
        max_length=255,
        null=True,
    )
    updated_by = models.CharField(
        max_length=255,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "mobile"
    REQUIRED_FIELDS = []

    def __str__(self):
        return str(self.mobile)

    @property
    def display_name(self):
        return self.full_name or str(self.mobile)

    class Meta:
        db_table = "user_master"


class OTPs(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mobile_number = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "otp"


class Sport(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(
        max_length=100,
        unique=True
    )
    icon = models.CharField(
        null=True,
        blank=True,
        max_length=200,
    )
    description = models.TextField(
        null=True,
        blank=True
    )
    display_order = models.PositiveIntegerField(
        default=0
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "sports"
        ordering = ["display_order", "name"]
    def __str__(self):
        return self.name

class Devices(AuditModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        UserMaster,
        on_delete=models.CASCADE,
        related_name="sessions",
        null=True,
        blank=True
    )
    device_id = models.CharField(
        max_length=200,
    )
    platform = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    app_version = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    fcm_token = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(
        blank=True,
        null=True
    )
    class Meta:
        db_table = "devices"
        indexes = [
            models.Index(fields=["device_id"]),
            models.Index(fields=["fcm_token"]),
            models.Index(fields=["user"])
        ]