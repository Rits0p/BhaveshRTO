import uuid

from django.db import models


class MessageLog(models.Model):
    class Status(models.TextChoices):
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE, related_name='message_logs')
    category = models.CharField(max_length=20)  # snapshot of the customer's category at send time
    message_body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    provider_response = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f'Message to {self.customer.name} [{self.status}]'
