from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    # The CRM lists intentionally load the complete customer register.
    # This ceiling protects the API while allowing the frontend to request it.
    max_page_size = 10000
