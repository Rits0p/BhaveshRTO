import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Sum

phone_validator = RegexValidator(
    regex=r'^\+?[0-9][0-9\s\-]{7,18}$',
    message='Enter a valid phone number (7-19 digits, optionally starting with +).',
)


class Customer(models.Model):
    class Category(models.TextChoices):
        INSURANCE = 'insurance', 'Insurance'
        PERMIT = 'permit', 'Permit'
        FITNESS = 'fitness', 'Fitness'
        PUC = 'puc', 'PUC'
        TAX = 'tax', 'Tax'
        FITNESS_PUC = 'fitness_puc', 'Fitness / PUC'  # legacy combined value
        LICENSE = 'license', 'License'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    contact_number = models.CharField(max_length=20, validators=[phone_validator], db_index=True)
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    # `category` remains the primary category for backwards compatibility.
    # `categories` records every service selected for this customer.
    categories = models.JSONField(default=list, blank=True)
    service_details = models.JSONField(default=dict, blank=True)
    vehicle_number = models.CharField(max_length=20, blank=True, null=True)
    reference_name = models.CharField(max_length=150, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True, db_index=True)
    amount_total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    # Cached/derived — always recomputed from Payment rows via recompute_amount_paid().
    # Never accept this as writable input on any endpoint.
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), editable=False)
    notes = models.TextField(blank=True, null=True)
    needs_reminder = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['end_date']),
            models.Index(fields=['contact_number']),
        ]
        ordering = ['-created_at']

    @property
    def amount_pending(self):
        return (self.amount_total or Decimal('0')) - (self.amount_paid or Decimal('0'))

    def recompute_amount_paid(self):
        """Recalculates amount_paid from the customer's Payment rows and
        persists it. Called after every payment create/update/delete.
        """
        total = self.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        self.amount_paid = total
        self.save(update_fields=['amount_paid', 'updated_at'])
        return self.amount_paid

    def __str__(self):
        return f'{self.name} ({self.category})'
