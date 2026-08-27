from rest_framework.views import exception_handler as drf_exception_handler


def _flatten_message(detail):
    """Collapse DRF's (possibly nested) error `detail` structure into a
    single human-readable string for the `message` field, while the full
    structure is still available under `errors` for field-level display.
    """
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return '; '.join(_flatten_message(item) for item in detail)
    if isinstance(detail, dict):
        parts = []
        for key, value in detail.items():
            flattened = _flatten_message(value)
            parts.append(flattened if key == 'non_field_errors' else f'{key}: {flattened}')
        return '; '.join(parts)
    return str(detail)


def api_exception_handler(exc, context):
    """Wraps DRF's default exception handler so every error response has a
    consistent `{ success: False, message: "...", errors: {...} }` shape,
    matching what the React frontend's toast notifications expect.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data.get('detail', response.data) if isinstance(response.data, dict) else response.data
    message = _flatten_message(detail) or 'Something went wrong.'

    response.data = {
        'success': False,
        'message': message,
        'errors': response.data if isinstance(response.data, dict) else None,
    }
    return response
