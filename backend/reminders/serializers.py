from rest_framework import serializers

from .models import MessageLog


class MessageLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageLog
        fields = ['id', 'customer', 'category', 'message_body', 'sent_at', 'status', 'provider_response']
