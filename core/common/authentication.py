# Location: core\common\authentication.py
"""
NexCart Custom Authentication
"""
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class OptionalJWTAuthentication(JWTAuthentication):
    """
    JWTAuthentication, but a missing/expired/garbage token is treated as
    "no credentials supplied" (request.user -> AnonymousUser) instead of
    raising 401.

    Use this - instead of bare `authentication_classes = []` - on AllowAny
    endpoints that must keep working for anonymous shoppers but should still
    recognize a *valid* token when one happens to be present (e.g. to log
    activity against the user, personalize results, etc). A blanket
    `authentication_classes = []` would ignore good tokens just as much as
    bad ones; this only swallows the failure case.

    Why this is needed at all: the frontend's axios interceptor
    (lib/api.js) attaches whatever access token is in sessionStorage to
    every request, regardless of whether the endpoint requires auth. Once
    that token expires, stock JWTAuthentication.authenticate() raises
    AuthenticationFailed - and DRF runs authentication BEFORE permission
    checks, so the view's `AllowAny` never gets a chance to apply and the
    request is rejected with 401 before reaching the view at all.
    """

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except AuthenticationFailed:
            return None
