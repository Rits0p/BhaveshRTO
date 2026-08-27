from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """Rate-limits login attempts per email address (not per IP), so a single
    attacker can't lock out or spam OTPs for someone else's account from many
    IPs, and a legitimate user retrying from one IP isn't unfairly limited
    alongside unrelated traffic.

    Configure the rate via REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login']
    (default: 5/hour, per the spec).
    """

    scope = 'login'

    def get_cache_key(self, request, view):
        email = str(request.data.get('email', '')).strip().lower()
        if not email:
            # No email provided — let serializer-level validation handle the
            # 400 instead of throttling on an empty/ambiguous key.
            return None
        return self.cache_format % {'scope': self.scope, 'ident': email}


class OTPRateThrottle(SimpleRateThrottle):
    """Rate-limits login-OTP verification per email address.

    Separate (looser) scope from step-1 login so a mistyped code or two
    doesn't eat into the password-attempt budget. Still tight enough to
    make brute-forcing a 6-digit code inside its 5-minute life unrealistic.
    Configure via REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['otp'].
    """

    scope = 'otp'

    def get_cache_key(self, request, view):
        email = str(request.data.get('email', '')).strip().lower()
        if not email:
            return None
        return self.cache_format % {'scope': self.scope, 'ident': email}


class RegisterRateThrottle(SimpleRateThrottle):
    """Rate-limits registration attempts per IP address.

    Prevents bulk account creation from a single source.
    Configure via REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['register']
    (default: 10/hour).
    """

    scope = 'register'

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class PasswordResetRateThrottle(SimpleRateThrottle):
    """Rate-limits password-reset requests per IP address.

    Prevents email flooding / user enumeration via timing attacks.
    Configure via REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['password_reset']
    (default: 5/hour).
    """

    scope = 'password_reset'

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}
