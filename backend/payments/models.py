import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import IntegrityError, models, transaction
from django.utils import timezone


def _generate_receipt_number():
    """Sequential, human-friendly receipt numbers: RCPT-000001, RCPT-000002, ...

    Uses a small retry loop (rather than a DB sequence table) since this is a
    single-admin, low-volume system — documented as a deliberate simplicity
    trade-off in DECISIONS.md.
    """
    for _ in range(5):
        next_seq = Payment.objects.count() + 1
        candidate = f"RCPT-{next_seq:06d}"
        if not Payment.objects.filter(receipt_number=candidate).exists():
            return candidate
    # Extremely unlikely fallback to guarantee uniqueness.
    return f"RCPT-{uuid.uuid4().hex[:10].upper()}"


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = 'cash', 'Cash'
        UPI = 'upi', 'UPI'
        CARD = 'card', 'Card'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_date = models.DateField(default=timezone.localdate)
    method = models.CharField(max_length=10, choices=Method.choices, blank=True, null=True)
    receipt_number = models.CharField(max_length=30, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            for _ in range(5):
                self.receipt_number = _generate_receipt_number()
                try:
                    with transaction.atomic():
                        super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    self.receipt_number = ''
                    continue
            raise IntegrityError('Could not generate a unique receipt number after several attempts.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.receipt_number} \u2014 \u20b9{self.amount} for {self.customer.name}'


def _generate_manual_receipt_number():
    """Sequential manual receipt numbers: MNL-000001, MNL-000002, ..."""
    for _ in range(5):
        next_seq = ManualReceipt.objects.count() + 1
        candidate = f"MNL-{next_seq:06d}"
        if not ManualReceipt.objects.filter(receipt_number=candidate).exists():
            return candidate
    return f"MNL-{uuid.uuid4().hex[:10].upper()}"


class ManualReceipt(models.Model):
    """Stores manually-generated receipts so they appear in the receipts list
    and their PDF can be re-downloaded at any time."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt_number = models.CharField(max_length=30, unique=True, editable=False)
    name = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=30, blank=True)
    vehicle_number = models.CharField(max_length=30, blank=True)
    service = models.CharField(max_length=255)
    date = models.DateField(default=timezone.localdate)
    amount_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    amount_pending = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    method = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            for _ in range(5):
                self.receipt_number = _generate_manual_receipt_number()
                try:
                    with transaction.atomic():
                        super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    self.receipt_number = ''
                    continue
            raise IntegrityError('Could not generate a unique manual receipt number.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.receipt_number} \u2014 {self.name}'
