import calendar
from collections import Counter
from datetime import datetime

from django.db.models import Q, Sum
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsTheOneAdmin
from customers.models import Customer
from payments.models import ManualReceipt, Payment

# Categories shown as dashboard cards, keyed by their frontend category value.
DASHBOARD_CATEGORIES = ['insurance', 'permit', 'fitness', 'puc', 'tax', 'license']


def _month_range(year, month):
    """Aware [start, end) datetime range covering `year`-`month` in the app's
    local timezone. Used instead of `__month` / Trunc* / dates(), which emit
    CONVERT_TZ() and return NULL because the MySQL server has no timezone
    tables loaded. Django converts the aware boundaries to UTC for the query,
    so this is correct regardless of DB timezone support.
    """
    start = timezone.make_aware(datetime(int(year), int(month), 1))
    next_month = (start.month % 12) + 1
    next_year = start.year + (1 if next_month == 1 else 0)
    end = timezone.make_aware(datetime(next_year, next_month, 1))
    return start, end


def _entered_customers(year, month):
    """Customers entered (based on start_date) in the selected period."""
    qs = Customer.objects.all()
    if year:
        qs = qs.filter(start_date__year=year)
    if month:
        qs = qs.filter(start_date__month=month)
    return qs


def _entered_receipts(year, month):
    """Manual receipts entered in the selected period based on date."""
    qs = ManualReceipt.objects.all()
    if year:
        qs = qs.filter(date__year=year)
    if month:
        qs = qs.filter(date__month=month)
    return qs


def _available_years():
    """Years that have entered customers (based on start_date) + manual receipts (based on date)."""
    years = set()
    for sd in Customer.objects.exclude(start_date__isnull=True).values_list('start_date', flat=True):
        years.add(sd.year)
    for d in ManualReceipt.objects.exclude(date__isnull=True).values_list('date', flat=True):
        years.add(d.year)
    return sorted(years, reverse=True)


def _category_summary(value, base=None):
    """Count + amounts for a category within `base` (default: all customers),
    using the exact same matching rule as customers/filters.py (primary
    `category` field OR the `categories` JSON list) so dashboard numbers
    always match the category pages.

    Note: a customer may belong to several categories (via the `categories`
    JSON list), so a customer's full amounts count towards every category
    they belong to. This mirrors what each category page shows.
    """
    if base is None:
        base = Customer.objects.all()
    qs = base.filter(Q(category=value) | Q(categories__icontains=f'"{value}"')).distinct()
    totals = qs.aggregate(total=Sum('amount_total'), paid=Sum('amount_paid'))
    total = float(totals['total'] or 0)
    paid = float(totals['paid'] or 0)
    return {
        'count': qs.count(),
        'total': f'{total:.2f}',
        'paid': f'{paid:.2f}',
        'pending': f'{max(total - paid, 0):.2f}',
    }


def _manual_receipt_summary(base=None):
    """Count + amounts for manual receipts (one-off customers entered through
    the Generate Manual Receipt flow, which have no category)."""
    if base is None:
        base = ManualReceipt.objects.all()
    qs = base
    totals = qs.aggregate(
        total=Sum('amount_total'), paid=Sum('amount_paid'), pending=Sum('amount_pending'),
    )
    total = float(totals['total'] or 0)
    paid = float(totals['paid'] or 0)
    pending = float(totals['pending'] or 0)
    return {
        'count': qs.count(),
        'total': f'{total:.2f}',
        'paid': f'{paid:.2f}',
        'pending': f'{pending:.2f}',
    }


class DashboardSummaryView(APIView):
    permission_classes = [IsTheOneAdmin]

    def get(self, request):
        # Optional year/month filter. Everything is scoped to the customer's
        # entered (created) date: customer counts, category cards, collection
        # (payments from the entered customers made in the period) and pending.
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        customers = _entered_customers(year, month)
        receipts = _entered_receipts(year, month)
        customer_ids = list(customers.values_list('id', flat=True))

        # Total customers = DB customers + manual receipts (one-off customers
        # recorded through the Generate Manual Receipt flow).
        total_customers = len(customer_ids) + receipts.count()

        period_payments = Payment.objects.filter(customer_id__in=customer_ids)
        # total_collection is the sum of payments for customers entered in this period
        db_total_collection = period_payments.aggregate(total=Sum('amount'))['total'] or 0
        manual_total_collection = receipts.aggregate(total=Sum('amount_paid'))['total'] or 0
        total_collection = db_total_collection + manual_total_collection

        # Pending: the outstanding balance of the entered customers.
        totals = customers.aggregate(total_amt=Sum('amount_total'), paid_amt=Sum('amount_paid'))
        db_total_amt = float(totals['total_amt'] or 0)
        db_paid_amt = float(totals['paid_amt'] or 0)
        
        manual_totals = receipts.aggregate(total_amt=Sum('amount_total'), paid_amt=Sum('amount_paid'))
        manual_total_amt = float(manual_totals['total_amt'] or 0)
        manual_paid_amt = float(manual_totals['paid_amt'] or 0)

        total_amt = db_total_amt + manual_total_amt
        paid_amt = db_paid_amt + manual_paid_amt

        years = _available_years()

        category_totals = {cat: _category_summary(cat, customers) for cat in DASHBOARD_CATEGORIES}
        category_totals['manual'] = _manual_receipt_summary(receipts)
        category_counts = {cat: info['count'] for cat, info in category_totals.items()}

        return Response({
            'success': True,
            'data': {
                'total_customers': total_customers,
                'totalCustomers': total_customers,
                'total_collection': f'{float(total_collection):.2f}',
                'totalCollection': f'{float(total_collection):.2f}',
                'pending_collection': f'{(total_amt - paid_amt):.2f}',
                'pendingCollection': f'{(total_amt - paid_amt):.2f}',
                'years': years,
                'category_counts': category_counts,
                'categoryCounts': category_counts,
                'category_totals': category_totals,
                'categoryTotals': category_totals,
            },
        })


class MonthlyCollectionView(APIView):
    permission_classes = [IsTheOneAdmin]

    def get(self, request):
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        # Payments from customers entered in the period
        qs = Payment.objects.filter(customer_id__in=_entered_customers(year, month))
        manual_qs = _entered_receipts(year, month)

        if month:
            y = int(year or timezone.localdate().year)
            m = int(month)
            rows = (
                qs.exclude(customer__start_date__isnull=True)
                .annotate(day=TruncDay('customer__start_date'))
                .values('day')
                .annotate(total=Sum('amount'))
            )
            by_day = {row['day'].day: float(row['total'] or 0) for row in rows if row['day'] is not None}
            
            manual_rows = (
                manual_qs.exclude(date__isnull=True)
                .annotate(day=TruncDay('date'))
                .values('day')
                .annotate(total=Sum('amount_paid'))
            )
            for row in manual_rows:
                if row['day'] is not None:
                    by_day[row['day'].day] = by_day.get(row['day'].day, 0) + float(row['total'] or 0)
                    
            data = [
                {'month': datetime(y, m, d).strftime('%d %b'), 'total': by_day.get(d, 0)}
                for d in range(1, calendar.monthrange(y, m)[1] + 1)
            ]
        else:
            rows = (
                qs.exclude(customer__start_date__isnull=True)
                .annotate(month=TruncMonth('customer__start_date'))
                .values('month')
                .annotate(total=Sum('amount'))
            )
            by_key = {
                (row['month'].year, row['month'].month): float(row['total'] or 0)
                for row in rows if row['month'] is not None
            }
            
            manual_rows = (
                manual_qs.exclude(date__isnull=True)
                .annotate(month=TruncMonth('date'))
                .values('month')
                .annotate(total=Sum('amount_paid'))
            )
            for row in manual_rows:
                if row['month'] is not None:
                    key = (row['month'].year, row['month'].month)
                    by_key[key] = by_key.get(key, 0) + float(row['total'] or 0)
                    
            years = sorted({y for y, _ in by_key})
            if year:
                years = [int(year)]
            if not years:
                years = [timezone.localdate().year]
            data = [
                {'month': datetime(y, m, 1).strftime('%b %Y'), 'total': by_key.get((y, m), 0)}
                for y in range(years[0], years[-1] + 1)
                for m in range(1, 13)
            ]
        return Response({'success': True, 'data': data})


class MonthlyCustomersView(APIView):
    permission_classes = [IsTheOneAdmin]

    def get(self, request):
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        qs = _entered_customers(year, month)
        manual_qs = _entered_receipts(year, month)

        monthly = Counter()
        daily = Counter()
        for start_date in qs.values_list('start_date', flat=True):
            if not start_date:
                continue
            monthly[(start_date.year, start_date.month)] += 1
            daily[(start_date.year, start_date.month, start_date.day)] += 1
            
        for date in manual_qs.values_list('date', flat=True):
            if not date:
                continue
            monthly[(date.year, date.month)] += 1
            daily[(date.year, date.month, date.day)] += 1

        if month:
            y = int(year or timezone.localdate().year)
            m = int(month)
            data = [
                {'month': datetime(y, m, d).strftime('%d %b'), 'count': daily.get((y, m, d), 0)}
                for d in range(1, calendar.monthrange(y, m)[1] + 1)
            ]
        else:
            years = sorted({y for y, _ in monthly})
            if year:
                years = [int(year)]
            if not years:
                years = [timezone.localdate().year]
            data = [
                {'month': datetime(y, m, 1).strftime('%b %Y'), 'count': monthly.get((y, m), 0)}
                for y in range(years[0], years[-1] + 1)
                for m in range(1, 13)
            ]
        return Response({'success': True, 'data': data})
