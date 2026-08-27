import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models

from .managers import AdminManager


class Admin(AbstractBaseUser, PermissionsMixin):
    """The single admin account for the whole system."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Two-step login: a pending email OTP. Only the SHA-256 hash of the code
    # is stored (never the code itself) plus the moment it was issued, so the
    # view can enforce expiry.
    login_otp_hash = models.CharField(max_length=64, blank=True, default='')
    login_otp_created_at = models.DateTimeField(null=True, blank=True)

    objects = AdminManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = 'Admin'
        verbose_name_plural = 'Admin'

    def save(self, *args, **kwargs):
        if self._state.adding and Admin.objects.exclude(pk=self.pk).exists():
            raise ValidationError('Only one Admin account is allowed for this system.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} <{self.email}>'
