from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.utils import timezone
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from payments.urls import payments_urlpatterns, receipts_urlpatterns


def health(request):
    return JsonResponse({'status': 'ok', 'timestamp': timezone.now().isoformat()})


urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/health', health, name='health'),

    path('api/auth/', include('accounts.urls')),
    path('api/dashboard/', include('dashboard.urls')),
    path('api/customers', include('customers.urls')),
    path('api/remarks', include('remarks.urls')),
    path('api/payments', include((payments_urlpatterns, 'payments'), namespace='payments')),
    path('api/receipts', include((receipts_urlpatterns, 'receipts'), namespace='receipts')),

    path('api/schema', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
