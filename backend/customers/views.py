import datetime

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.pagination import StandardResultsSetPagination
from common.permissions import IsTheOneAdmin

from .filters import CustomerFilter
from .models import Customer
from .serializers import CATEGORY_SERIALIZERS, BaseCustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    """Master CRUD for customers, plus two custom actions:

    - GET  /api/customers/expiring-soon/       (list-level)
    - POST /api/customers/{id}/send-reminder/  (detail-level)

    Field-level filtering per category (the "category pages" requirement) is
    enforced by swapping in a category-specific serializer for the `list`
    action only — create/retrieve/update/delete always use the full field
    set, since those power the master edit form.
    """

    queryset = Customer.objects.all()
    serializer_class = BaseCustomerSerializer
    permission_classes = [IsTheOneAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = CustomerFilter

    def finalize_response(self, request, response, *args, **kwargs):
        """Customer records must always reflect the current database state."""
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    def get_serializer_class(self):
        if self.action == 'list':
            category = self.request.query_params.get('category')
            if category in CATEGORY_SERIALIZERS:
                return CATEGORY_SERIALIZERS[category]
        return BaseCustomerSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            paginated = self.get_paginated_response(serializer.data)
            return Response({
                'success': True,
                'total': paginated.data['count'],
                'next': paginated.data['next'],
                'previous': paginated.data['previous'],
                'data': paginated.data['results'],
            })
        return Response({'success': True, 'total': queryset.count(), 'data': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        return Response(
            {'success': True, 'message': 'Customer created.', 'data': self.get_serializer(customer).data},
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response({'success': True, 'data': self.get_serializer(instance).data})

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        return Response({'success': True, 'message': 'Customer updated.', 'data': self.get_serializer(customer).data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({'success': True, 'message': 'Customer deleted.'})

    @action(detail=False, methods=['get'], url_path='expiring-soon')
    def expiring_soon(self, request):
        days = int(request.query_params.get('days', 30))
        category = request.query_params.get('category')

        today = timezone.localdate()
        future = today + datetime.timedelta(days=days)

        qs = Customer.objects.filter(end_date__range=[today, future])
        if category:
            qs = qs.filter(category=category)

        serializer_cls = CATEGORY_SERIALIZERS.get(category, BaseCustomerSerializer)
        serializer = serializer_cls(qs, many=True)
        return Response({'success': True, 'days': days, 'total': qs.count(), 'data': serializer.data})

    @action(detail=True, methods=['post'], url_path='send-reminder')
    def send_reminder(self, request, pk=None):
        from reminders.serializers import MessageLogSerializer
        from reminders.services import send_reminder as send_reminder_service

        customer = self.get_object()
        log, success = send_reminder_service(customer)

        return Response(
            {
                'success': success,
                'message': f'Reminder sent to {customer.contact_number}.' if success else 'WhatsApp message failed to send.',
                'data': MessageLogSerializer(log).data,
            },
            status=status.HTTP_200_OK if success else status.HTTP_502_BAD_GATEWAY,
        )
