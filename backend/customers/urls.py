from django.urls import path

from .views import CustomerViewSet

# Defined explicitly (rather than via DRF's DefaultRouter) so every route
# matches the existing React frontend's no-trailing-slash convention exactly
# (e.g. `/customers`, `/customers/${id}`) — DRF's router always expects a
# slash-terminated mount point, which isn't compatible with that convention.
customer_list = CustomerViewSet.as_view({'get': 'list', 'post': 'create'})
customer_detail = CustomerViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})
customer_expiring_soon = CustomerViewSet.as_view({'get': 'expiring_soon'})
customer_send_reminder = CustomerViewSet.as_view({'post': 'send_reminder'})

urlpatterns = [
    path('', customer_list, name='customer-list'),
    path('/expiring-soon', customer_expiring_soon, name='customer-expiring-soon'),
    path('/<uuid:pk>', customer_detail, name='customer-detail'),
    path('/<uuid:pk>/send-reminder', customer_send_reminder, name='customer-send-reminder'),
]
