import django_filters

from .models import Customer


class CustomerFilter(django_filters.FilterSet):
    category = django_filters.ChoiceFilter(choices=Customer.Category.choices, method='filter_category')
    search = django_filters.CharFilter(method='filter_search')
    # Month-of-year range filters (1-12) on start_date, matching any year so
    # the All Customers page can show "everything entered between e.g. Jan and May".
    month_from = django_filters.CharFilter(method='filter_month_from')
    month_to = django_filters.CharFilter(method='filter_month_to')

    class Meta:
        model = Customer
        fields = ['category']

    def filter_month_from(self, queryset, name, value):
        month = self._parse_month(value)
        if month is None:
            return queryset
        return queryset.filter(start_date__isnull=False, start_date__month__gte=month)

    def filter_month_to(self, queryset, name, value):
        month = self._parse_month(value)
        if month is None:
            return queryset
        return queryset.filter(start_date__isnull=False, start_date__month__lte=month)

    @staticmethod
    def _parse_month(value):
        try:
            month = int(value)
        except (TypeError, ValueError):
            return None
        return month if 1 <= month <= 12 else None

    def filter_search(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(name__icontains=value) | Q(contact_number__icontains=value)
            | Q(vehicle_number__icontains=value) | Q(reference_name__icontains=value)
        )

    def filter_category(self, queryset, name, value):
        # JSON "contains" is not supported by every database Django supports.
        # Matching the serialized list works consistently because category values
        # are fixed choices and cannot be substrings of one another.
        from django.db.models import Q
        return queryset.filter(Q(category=value) | Q(categories__icontains=f'"{value}"')).distinct()
