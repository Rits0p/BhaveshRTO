from rest_framework import serializers

from .models import Customer


class BaseCustomerSerializer(serializers.ModelSerializer):
    """Full read/write serializer used by the master form (create/edit) and
    the "All Customers" list. `amount_paid`/`amount_pending` are always
    read-only/derived — never accepted as writable input.
    """
    amount_pending = serializers.SerializerMethodField()
    # Remarks are read-only on the customer endpoints; full CRUD lives on the
    # dedicated /api/remarks endpoints. These fields power the customer-list
    # remarks column.
    remarks_count = serializers.SerializerMethodField()
    latest_remark = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'contact_number', 'category', 'vehicle_number',
            'categories', 'service_details', 'reference_name',
            'start_date', 'end_date', 'amount_total', 'amount_paid', 'amount_pending',
            'notes', 'needs_reminder', 'created_at', 'updated_at',
            'remarks_count', 'latest_remark',
        ]
        read_only_fields = ['amount_paid', 'needs_reminder', 'created_at', 'updated_at', 'remarks_count', 'latest_remark']

    def get_amount_pending(self, obj):
        return str(obj.amount_pending)

    def get_remarks_count(self, obj):
        return obj.remarks.count()

    def get_latest_remark(self, obj):
        latest = obj.remarks.first()
        return latest.text if latest else None

    def validate(self, attrs):
        categories = attrs.get('categories')
        if categories is not None:
            valid_categories = {value for value, _ in Customer.Category.choices}
            if not isinstance(categories, list) or not categories or any(category not in valid_categories for category in categories):
                raise serializers.ValidationError({'categories': 'Select at least one valid category.'})
            attrs['categories'] = list(dict.fromkeys(categories))
            attrs['category'] = attrs['categories'][0]
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({'end_date': 'End date cannot be before start date.'})
        return attrs


# ─── Category-specific serializers ────────────────────────────────────────
# Per spec: category pages must be field-filtered server-side so there is no
# data leakage even if the frontend is compromised or buggy. Each serializer
# below defines its own field allowlist; the ViewSet picks one dynamically
# based on the `?category=` query param.

class InsuranceCustomerSerializer(serializers.ModelSerializer):
    amount_pending = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'contact_number', 'vehicle_number',
            'start_date', 'end_date', 'amount_total', 'amount_paid', 'amount_pending',
            'needs_reminder', 'notes',
        ]
        read_only_fields = fields

    def get_amount_pending(self, obj):
        return str(obj.amount_pending)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        category = request.query_params.get('category') if request else instance.category
        details = (instance.service_details or {}).get(category, {})
        data['start_date'] = details.get('start_date') or data.get('start_date')
        data['end_date'] = details.get('end_date') or data.get('end_date')
        return data


class PermitCustomerSerializer(InsuranceCustomerSerializer):
    """Permit exposes the same field set as Insurance."""


class FitnessPucCustomerSerializer(serializers.ModelSerializer):
    """Per PRD: this page must show *nothing else* beyond these four fields."""

    class Meta:
        model = Customer
        fields = ['id', 'name', 'contact_number', 'start_date', 'end_date', 'needs_reminder']
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        details = (instance.service_details or {}).get('fitness_puc', {})
        data['start_date'] = details.get('start_date') or data.get('start_date')
        data['end_date'] = details.get('end_date') or data.get('end_date')
        return data


class SplitServiceSerializer(serializers.ModelSerializer):
    """Shared minimal serializer for the individually split service pages
    (Fitness, PUC, Tax). Only name/contact and the service-specific dates are
    exposed, matching the data-minimal category-page requirement.

    `details_key` selects which service_details bucket to read dates from;
    `legacy_keys` are the pre-split bucket names to fall back to so records
    saved before the split keep showing their dates.
    """

    details_key = None
    legacy_keys = ()

    class Meta:
        model = Customer
        fields = ['id', 'name', 'contact_number', 'start_date', 'end_date', 'needs_reminder']
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        details = instance.service_details or {}
        service = details.get(self.details_key) or {}
        for legacy_key in self.legacy_keys:
            if service:
                break
            service = details.get(legacy_key) or {}
        data['start_date'] = service.get('start_date') or data.get('start_date')
        data['end_date'] = service.get('end_date') or data.get('end_date')
        return data


class FitnessCustomerSerializer(SplitServiceSerializer):
    details_key = 'fitness'
    legacy_keys = ('fitness_puc',)


class PucCustomerSerializer(SplitServiceSerializer):
    details_key = 'puc'
    legacy_keys = ('fitness_puc',)


class TaxCustomerSerializer(SplitServiceSerializer):
    details_key = 'tax'
    legacy_keys = ('permit',)

    class Meta(SplitServiceSerializer.Meta):
        fields = ['id', 'name', 'contact_number', 'vehicle_number', 'start_date', 'end_date', 'needs_reminder']
        read_only_fields = fields


class LicenseCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'contact_number', 'start_date', 'end_date', 'needs_reminder']
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        details = (instance.service_details or {}).get('license', {})
        data['start_date'] = details.get('start_date') or data.get('start_date')
        data['end_date'] = details.get('end_date') or data.get('end_date')
        return data


CATEGORY_SERIALIZERS = {
    Customer.Category.INSURANCE: InsuranceCustomerSerializer,
    Customer.Category.PERMIT: PermitCustomerSerializer,
    Customer.Category.FITNESS: FitnessCustomerSerializer,
    Customer.Category.PUC: PucCustomerSerializer,
    Customer.Category.TAX: TaxCustomerSerializer,
    Customer.Category.FITNESS_PUC: FitnessPucCustomerSerializer,
    Customer.Category.LICENSE: LicenseCustomerSerializer,
}
