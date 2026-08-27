from django.urls import path

from .views import RemarkDetailView, RemarkListCreateView

# Matches the repo's no-trailing-slash convention used everywhere else.
urlpatterns = [
    path('', RemarkListCreateView.as_view(), name='remark-list-create'),
    path('/<uuid:pk>', RemarkDetailView.as_view(), name='remark-detail'),
]
