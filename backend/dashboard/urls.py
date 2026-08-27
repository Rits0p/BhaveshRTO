from django.urls import path

from . import views

urlpatterns = [
    path('summary', views.DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('monthly-collection', views.MonthlyCollectionView.as_view(), name='dashboard-monthly-collection'),
    path('monthly-customers', views.MonthlyCustomersView.as_view(), name='dashboard-monthly-customers'),
]
