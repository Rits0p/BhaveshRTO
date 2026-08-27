from decimal import Decimal

from rest_framework import serializers

from customers.models import Customer

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'customer', 'amount', 'payment_date', 'method', 'receipt_number', 'created_at']
        read_only_fields = ['receipt_number', 'created_at']


class RecordPaymentSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    payment_date = serializers.DateField(required=False)
    method = serializers.ChoiceField(choices=Payment.Method.choices, required=False, allow_null=True)

    def validate_customer_id(self, value):
        if not Customer.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Customer not found.')
        return value
