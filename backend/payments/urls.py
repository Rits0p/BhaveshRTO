from django.urls import path

from . import views

# Mounted twice from config/urls.py: once under /api/payments (just the
# create endpoint) and once under /api/receipts (the read endpoints).
payments_urlpatterns = [
    path('', views.RecordPaymentView.as_view(), name='record-payment'),
]

receipts_urlpatterns = [
    path('', views.OverallReceiptsView.as_view(), name='overall-receipts'),
    path('/manual', views.SaveManualReceiptView.as_view(), name='manual-receipt-save'),
    path('/manual-pdf', views.ManualReceiptPDFView.as_view(), name='manual-receipt-pdf'),
    path('/manual/<uuid:receipt_id>', views.UpdateManualReceiptView.as_view(), name='manual-receipt-update'),
    path('/manual/<uuid:receipt_id>/pdf', views.ManualReceiptPDFByIdView.as_view(), name='manual-receipt-pdf-by-id'),
    path('/manual/<uuid:receipt_id>/send-whatsapp', views.SendManualReceiptWhatsAppView.as_view(), name='manual-receipt-send-whatsapp'),
    path('/<uuid:customer_id>/amount', views.UpdateCustomerReceiptAmountView.as_view(), name='customer-receipt-amount'),
    path('/<uuid:customer_id>', views.CustomerReceiptView.as_view(), name='customer-receipt'),
    path('/<uuid:customer_id>/pdf', views.CustomerReceiptPDFView.as_view(), name='customer-receipt-pdf'),
    path('/<uuid:customer_id>/send-whatsapp', views.SendCustomerReceiptWhatsAppView.as_view(), name='customer-receipt-send-whatsapp'),
]

