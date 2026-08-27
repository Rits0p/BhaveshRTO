from rest_framework.permissions import BasePermission


class IsTheOneAdmin(BasePermission):
    """Grants access only to the single authenticated Admin account.

    Since this system enforces exactly one Admin row for its entire
    lifetime, this is functionally equivalent to IsAuthenticated, but is
    named explicitly per spec and is the single choke point where any
    future extra checks on the admin account (e.g. is_verified) could be
    added without touching every view.
    """

    message = 'Authentication credentials were not provided or are invalid.'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(
            user
            and getattr(user, 'is_authenticated', False)
            and getattr(user, 'is_verified', False)
        )
