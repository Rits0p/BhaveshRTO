import datetime
from decimal import Decimal, InvalidOperation

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsTheOneAdmin
from customers.models import Customer

from .models import ManualReceipt, Payment
from .serializers import PaymentSerializer, RecordPaymentSerializer
from .services import generate_manual_pdf_receipt, generate_pdf_receipt


class RecordPaymentView(APIView):
    """POST /api/payments/ — records a payment and recomputes the
    customer's cached amount_paid/amount_pending from the Payment rows.
    """
    permission_classes = [IsTheOneAdmin]

    def post(self, request):
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        customer = Customer.objects.get(pk=data['customer_id'])
        payment_kwargs = {'customer': customer, 'amount': data['amount'], 'method': data.get('method')}
        if data.get('payment_date'):
            payment_kwargs['payment_date'] = data['payment_date']
        payment = Payment.objects.create(**payment_kwargs)
        customer.recompute_amount_paid()

        return Response(
            {
                'success': True,
                'message': 'Payment recorded.',
                'data': PaymentSerializer(payment).data,
                'amount_pending': str(customer.amount_pending),
            },
            status=status.HTTP_201_CREATED,
        )


class OverallReceiptsView(APIView):
    """GET /api/receipts/ — overall collected/pending summary across all
    customers AND manual receipts combined. Each row carries a ``type``
    field ('customer' or 'manual') so the frontend can filter them.
    """
    permission_classes = [IsTheOneAdmin]

    def get(self, request):
        rows = []
        grand_total = grand_paid = grand_pending = 0

        # ── Customer receipts ─────────────────────────────────────────────
        for c in Customer.objects.all():
            total = float(c.amount_total or 0)
            paid = float(c.amount_paid or 0)
            pending = total - paid
            grand_total += total
            grand_paid += paid
            grand_pending += pending
            rows.append({
                'id': str(c.id),
                'type': 'customer',
                'name': c.name,
                'contact_number': c.contact_number,
                'category': c.category,    # used by frontend for badge
                'categories': c.categories or [c.category],
                'service': None,           # n/a for customer receipts
                'vehicle_number': c.vehicle_number,
                'amount_total': total,
                'amount_paid': paid,
                'amount_pending': pending,
            })

        # ── Manual receipts ───────────────────────────────────────────────
        for m in ManualReceipt.objects.all():
            total = float(m.amount_total or 0)
            paid = float(m.amount_paid or 0)
            pending = float(m.amount_pending or 0)
            grand_total += total
            grand_paid += paid
            grand_pending += pending
            rows.append({
                'id': str(m.id),
                'type': 'manual',
                'name': m.name,
                'contact_number': m.contact_number,
                'category': None,          # n/a for manual receipts
                'service': m.service,      # shown instead of category
                'vehicle_number': m.vehicle_number,
                'amount_total': total,
                'amount_paid': paid,
                'amount_pending': pending,
                'receipt_number': m.receipt_number,
                'date': m.date.strftime('%Y-%m-%d'),
                'method': m.method,
            })

        return Response({
            'success': True,
            'data': {
                'summary': {'grandTotal': grand_total, 'grandPaid': grand_paid, 'grandPending': grand_pending},
                'customers': rows,
            },
        })


class UpdateCustomerReceiptAmountView(APIView):
    """PUT /api/receipts/<uuid:customer_id>/amount — adjust the Total and/or
    Paid amounts shown on a customer receipt.

    ``amount_total`` updates Customer.amount_total. ``amount_paid`` is
    reconciled against the Payment rows (it is a cached/derived value): a
    higher value creates a top-up Payment, a lower value shrinks the newest
    Payment(s). amount_pending is recomputed afterwards.
    """
    permission_classes = [IsTheOneAdmin]

    def _dec(self, val):
        try:
            return Decimal(str(val or 0))
        except InvalidOperation:
            return Decimal('0.00')

    def put(self, request, customer_id):
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'success': False, 'message': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)

        amount_total = request.data.get('amount_total')
        amount_paid = request.data.get('amount_paid')

        if amount_total is not None:
            total = self._dec(amount_total)
            if total < 0:
                return Response({'success': False, 'message': 'Total amount cannot be negative.'}, status=status.HTTP_400_BAD_REQUEST)
            customer.amount_total = total
            customer.save(update_fields=['amount_total'])

        if amount_paid is not None:
            new_paid = self._dec(amount_paid)
            if new_paid < 0:
                return Response({'success': False, 'message': 'Paid amount cannot be negative.'}, status=status.HTTP_400_BAD_REQUEST)
            delta = new_paid - customer.amount_paid
            if delta > 0:
                # Overpay the receipt: add a top-up Payment for the difference.
                Payment.objects.create(customer=customer, amount=delta)
            elif delta < 0:
                # Underpay: shrink the newest Payment(s) until the difference
                # is covered, deleting any that drop to zero.
                remaining = -delta
                for p in customer.payments.order_by('-payment_date', '-created_at'):
                    if remaining <= 0:
                        break
                    take = min(p.amount, remaining)
                    p.amount -= take
                    remaining -= take
                    if p.amount <= 0:
                        p.delete()
                    else:
                        p.save(update_fields=['amount'])
            customer.recompute_amount_paid()

        customer.refresh_from_db()
        return Response({
            'success': True,
            'message': 'Receipt amount updated successfully.',
            'data': {
                'id': str(customer.id),
                'amount_total': str(customer.amount_total),
                'amount_paid': str(customer.amount_paid),
                'amount_pending': str(customer.amount_pending),
            },
        })


class CustomerReceiptView(APIView):
    """GET /api/receipts/{customer_id}/ — JSON receipt breakdown for one customer."""
    permission_classes = [IsTheOneAdmin]

    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'success': False, 'message': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)

        payments = customer.payments.all().order_by('-payment_date')
        total_paid = sum(float(p.amount) for p in payments)
        total_pending = float(customer.amount_total or 0) - total_paid

        return Response({
            'success': True,
            'data': {
                'customer': {
                    'id': str(customer.id),
                    'name': customer.name,
                    'contact_number': customer.contact_number,
                    'category': customer.category,
                    'vehicle_number': customer.vehicle_number,
                    'start_date': customer.start_date,
                    'end_date': customer.end_date,
                    'amount_total': customer.amount_total,
                },
                'payments': PaymentSerializer(payments, many=True).data,
                'totalPaid': f'{total_paid:.2f}',
                'totalPending': f'{total_pending:.2f}',
            },
        })


class CustomerReceiptPDFView(APIView):
    """GET /api/receipts/{customer_id}/pdf/ — PDF receipt served inline."""
    permission_classes = [IsTheOneAdmin]

    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'success': False, 'message': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)

        payments = list(customer.payments.all().order_by('-payment_date'))
        total_paid = sum(float(p.amount) for p in payments)
        total_pending = float(customer.amount_total or 0) - total_paid

        admin_name = getattr(request.user, 'name', None) or 'Bhavesh Solanki'
        pdf_bytes = generate_pdf_receipt(customer, payments, total_paid, total_pending, admin_name=admin_name)

        filename = f"receipt_{customer.name.replace(' ', '_')}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class ManualReceiptPDFView(APIView):
    """POST /api/receipts/manual-pdf — generates a PDF from manually entered
    form data, saves a ManualReceipt row so it appears in the receipts list,
    and returns the PDF bytes inline.

    Expected JSON body fields:
        name, contact_number, vehicle_number, service, date (YYYY-MM-DD),
        amount_total, amount_paid, amount_pending, method
    """
    permission_classes = [IsTheOneAdmin]

    def post(self, request):
        form_data = request.data

        if not form_data.get('name'):
            return Response(
                {'success': False, 'message': 'Customer name is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Parse & coerce types ──────────────────────────────────────────
        def _dec(val):
            try:
                return Decimal(str(val or 0))
            except InvalidOperation:
                return Decimal('0.00')

        raw_date = form_data.get('date') or ''
        try:
            pay_date = datetime.datetime.strptime(raw_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pay_date = datetime.date.today()

        # ── Persist to DB so the record shows up in the receipts list ─────
        manual = ManualReceipt.objects.create(
            name=form_data.get('name', '').strip(),
            contact_number=form_data.get('contact_number', '').strip(),
            vehicle_number=form_data.get('vehicle_number', '').strip(),
            service=form_data.get('service', '').strip(),
            date=pay_date,
            amount_total=_dec(form_data.get('amount_total')),
            amount_paid=_dec(form_data.get('amount_paid')),
            amount_pending=_dec(form_data.get('amount_pending')),
            method=form_data.get('method', '').strip(),
        )

        # Use the DB-assigned receipt number in the PDF
        pdf_form_data = dict(form_data)
        pdf_form_data['receipt_number'] = manual.receipt_number

        admin_name = getattr(request.user, 'name', None) or 'Bhavesh Solanki'
        pdf_bytes = generate_manual_pdf_receipt(pdf_form_data, admin_name=admin_name)

        filename = f"manual_receipt_{manual.name.replace(' ', '_')}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class SaveManualReceiptView(APIView):
    """POST /api/receipts/manual — saves a manual receipt to DB without generating PDF."""
    permission_classes = [IsTheOneAdmin]

    def post(self, request):
        form_data = request.data
        if not form_data.get('name'):
            return Response(
                {'success': False, 'message': 'Customer name is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        def _dec(val):
            try:
                return Decimal(str(val or 0))
            except InvalidOperation:
                return Decimal('0.00')

        raw_date = form_data.get('date') or ''
        try:
            pay_date = datetime.datetime.strptime(raw_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pay_date = datetime.date.today()

        manual = ManualReceipt.objects.create(
            name=form_data.get('name', '').strip(),
            contact_number=form_data.get('contact_number', '').strip(),
            vehicle_number=form_data.get('vehicle_number', '').strip(),
            service=form_data.get('service', '').strip(),
            date=pay_date,
            amount_total=_dec(form_data.get('amount_total')),
            amount_paid=_dec(form_data.get('amount_paid')),
            amount_pending=_dec(form_data.get('amount_pending')),
            method=form_data.get('method', '').strip(),
        )

        return Response({
            'success': True,
            'message': 'Manual receipt saved successfully.',
            'data': {
                'id': str(manual.id),
                'receipt_number': manual.receipt_number,
            }
        }, status=status.HTTP_201_CREATED)


class UpdateManualReceiptView(APIView):
    """PUT /api/receipts/manual/<uuid:receipt_id> — updates an existing
    manual receipt in the DB. amount_pending is always recomputed from
    amount_total - amount_paid so the stored value can't go stale.
    """
    permission_classes = [IsTheOneAdmin]

    def _dec(self, val):
        try:
            return Decimal(str(val or 0))
        except InvalidOperation:
            return Decimal('0.00')

    def put(self, request, receipt_id):
        try:
            manual = ManualReceipt.objects.get(pk=receipt_id)
        except ManualReceipt.DoesNotExist:
            return Response({'success': False, 'message': 'Manual receipt not found.'}, status=status.HTTP_404_NOT_FOUND)

        form_data = request.data
        if not form_data.get('name'):
            return Response(
                {'success': False, 'message': 'Customer name is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_date = form_data.get('date') or ''
        try:
            pay_date = datetime.datetime.strptime(raw_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pay_date = manual.date

        total = self._dec(form_data.get('amount_total'))
        paid = self._dec(form_data.get('amount_paid'))

        manual.name = form_data.get('name', manual.name).strip()
        manual.contact_number = form_data.get('contact_number', manual.contact_number).strip()
        manual.vehicle_number = form_data.get('vehicle_number', manual.vehicle_number).strip()
        manual.service = form_data.get('service', manual.service).strip()
        manual.date = pay_date
        manual.amount_total = total
        manual.amount_paid = paid
        manual.amount_pending = max(Decimal('0.00'), total - paid)
        manual.method = form_data.get('method', manual.method).strip()
        manual.save()

        return Response({
            'success': True,
            'message': 'Manual receipt updated successfully.',
            'data': {
                'id': str(manual.id),
                'receipt_number': manual.receipt_number,
            }
        })


class ManualReceiptPDFByIdView(APIView):
    """GET /api/receipts/manual/<uuid:receipt_id>/pdf — re-downloads the PDF
    for an already-saved ManualReceipt by its ID.
    """
    permission_classes = [IsTheOneAdmin]

    def get(self, request, receipt_id):
        try:
            manual = ManualReceipt.objects.get(pk=receipt_id)
        except ManualReceipt.DoesNotExist:
            return Response({'success': False, 'message': 'Manual receipt not found.'}, status=status.HTTP_404_NOT_FOUND)

        form_data = {
            'name': manual.name,
            'contact_number': manual.contact_number,
            'vehicle_number': manual.vehicle_number,
            'service': manual.service,
            'date': manual.date.strftime('%Y-%m-%d'),
            'amount_total': float(manual.amount_total),
            'amount_paid': float(manual.amount_paid),
            'amount_pending': float(manual.amount_pending),
            'method': manual.method,
            'receipt_number': manual.receipt_number,
        }

        admin_name = getattr(request.user, 'name', None) or 'Bhavesh Solanki'
        pdf_bytes = generate_manual_pdf_receipt(form_data, admin_name=admin_name)

        filename = f"manual_receipt_{manual.name.replace(' ', '_')}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class SendCustomerReceiptWhatsAppView(APIView):
    """POST /api/receipts/<uuid:customer_id>/send-whatsapp — generates the
    customer receipt PDF, uploads it to WhatsApp, and sends it as a
    document message to the customer's contact_number.
    """
    permission_classes = [IsTheOneAdmin]

    def post(self, request, customer_id):
        from reminders.services import send_receipt_via_whatsapp
        success, message = send_receipt_via_whatsapp('customer', customer_id)
        return Response(
            {'success': success, 'message': message},
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST,
        )


class SendManualReceiptWhatsAppView(APIView):
    """POST /api/receipts/manual/<uuid:receipt_id>/send-whatsapp — generates
    the manual receipt PDF, uploads it to WhatsApp, and sends it as a
    document message to the receipt's contact_number.
    """
    permission_classes = [IsTheOneAdmin]

    def post(self, request, receipt_id):
        from reminders.services import send_receipt_via_whatsapp
        success, message = send_receipt_via_whatsapp('manual', receipt_id)
        return Response(
            {'success': success, 'message': message},
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST,
        )

