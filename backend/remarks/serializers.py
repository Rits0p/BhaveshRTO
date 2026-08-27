from rest_framework import serializers

from .models import Remark


class RemarkSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    vehicle_number = serializers.CharField(source='customer.vehicle_number', read_only=True)

    class Meta:
        model = Remark
        fields = ['id', 'customer', 'customer_name', 'vehicle_number', 'text', 'created_at', 'updated_at']
        read_only_fields = ['id', 'customer_name', 'vehicle_number', 'created_at', 'updated_at']
