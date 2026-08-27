import uuid

from django.db import models


class Remark(models.Model):
    """A free-text note attached to a Customer record.

    Remarks are linked to a customer (not free-floating) so they can be
    viewed both on the dedicated Remarks page and inside the customer list.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='remarks')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Remark on {self.customer.name}: {self.text[:50]}'
